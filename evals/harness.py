from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.policy import check_request
from app.rag import mentions_outside_city_of_adelaide, search_council_sources


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"


@dataclass
class CaseResult:
    skill: str
    case_id: str
    passed: bool
    failures: list[str]
    observed: dict[str, Any]


def run_eval_harness(skill_filter: str | None = None) -> dict[str, Any]:
    skill_dirs = sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir())
    if skill_filter:
        skill_dirs = [path for path in skill_dirs if path.name == skill_filter]

    results: list[CaseResult] = []
    for skill_dir in skill_dirs:
        eval_dir = skill_dir / "evals"
        input_path = eval_dir / "input.json"
        tools_path = eval_dir / "expected_tools.json"
        output_path = eval_dir / "expected_output.json"
        if not (input_path.exists() and tools_path.exists() and output_path.exists()):
            continue

        input_cases = {case["id"]: case for case in _load_cases(input_path)}
        tool_cases = {case["id"]: case for case in _load_cases(tools_path)}
        output_cases = {case["id"]: case for case in _load_cases(output_path)}

        all_case_ids = sorted(set(input_cases) | set(tool_cases) | set(output_cases))
        for case_id in all_case_ids:
            failures: list[str] = []
            input_case = input_cases.get(case_id)
            if input_case is None:
                failures.append("Missing input case")
                results.append(CaseResult(skill_dir.name, case_id, False, failures, {}))
                continue

            expected_tools = tool_cases.get(case_id, {})
            expected_output = output_cases.get(case_id, {})
            observed = _run_case(skill_dir.name, input_case)

            failures.extend(_validate_tools(expected_tools, observed.get("called_tools", [])))
            failures.extend(_validate_output(expected_output, observed))
            results.append(CaseResult(skill_dir.name, case_id, not failures, failures, observed))

    passed = sum(1 for result in results if result.passed)
    summary = {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": [
            {
                "skill": result.skill,
                "case_id": result.case_id,
                "passed": result.passed,
                "failures": result.failures,
                "observed": result.observed,
            }
            for result in results
        ],
    }
    return summary


def _run_case(skill: str, input_case: dict[str, Any]) -> dict[str, Any]:
    if skill == "policy_guard":
        return _run_policy_case(input_case)
    if skill == "waste_and_recycling":
        return _run_waste_case(input_case)
    return {"called_tools": [], "status": "unsupported_skill"}


def _run_policy_case(input_case: dict[str, Any]) -> dict[str, Any]:
    decision = check_request(
        text=input_case["user_prompt"],
        requested_tool=input_case.get("requested_tool"),
        role="public_user",
        environment="development",
    )
    return {
        "called_tools": [],
        "decision": decision.get("decision"),
        "reason": decision.get("reason"),
        "redactions": decision.get("redactions", []),
        "answer_text": decision.get("sanitized_input", ""),
        "source_urls": [],
    }


def _run_waste_case(input_case: dict[str, Any]) -> dict[str, Any]:
    question = input_case["user_prompt"]
    context = input_case.get("context", {})
    council = context.get("council", "City of Adelaide")

    called_tools = ["policy_guard.check_request"]
    decision = check_request(
        text=question,
        requested_tool="rag.search",
        role="public_user",
        environment="development",
    )

    if decision["decision"] == "block":
        return {
            "called_tools": called_tools,
            "decision": decision["decision"],
            "reason": decision["reason"],
            "status": "blocked",
            "answer_text": "I cannot help with that request because it violates CouncilQ safety policy.",
            "source_urls": [],
        }

    if decision["decision"] == "requires_human_approval":
        return {
            "called_tools": called_tools,
            "decision": decision["decision"],
            "reason": decision["reason"],
            "status": "requires_human_approval",
            "answer_text": "That action requires human approval before CouncilQ can continue.",
            "source_urls": [],
        }

    if str(council).strip().lower() != "city of adelaide" or mentions_outside_city_of_adelaide(question.lower()):
        return {
            "called_tools": called_tools,
            "decision": decision["decision"],
            "reason": decision["reason"],
            "status": "clarification_required",
            "answer_text": "CouncilQ is currently scoped to the City of Adelaide. Please confirm the property or service is in the City of Adelaide council area before I continue.",
            "source_urls": [],
        }

    called_tools.append("rag.search")
    retrieval = search_council_sources(decision["sanitized_input"], fetch_live_pages=False)
    return {
        "called_tools": called_tools,
        "decision": decision["decision"],
        "reason": decision["reason"],
        "status": retrieval["status"],
        "answer_text": retrieval.get("message", ""),
        "source_urls": [source["url"] for source in retrieval.get("sources", [])],
    }


def _validate_tools(expected_case: dict[str, Any], called_tools: list[str]) -> list[str]:
    failures: list[str] = []

    expected_order = [step["tool"] for step in expected_case.get("expected_tool_trajectory", [])]
    if expected_order and not _contains_subsequence(called_tools, expected_order):
        failures.append(
            f"Tool trajectory mismatch. expected subsequence={expected_order}, observed={called_tools}"
        )

    forbidden = expected_case.get("must_not_call", [])
    for tool in forbidden:
        if tool in called_tools:
            failures.append(f"Forbidden tool called: {tool}")

    return failures


def _validate_output(expected_case: dict[str, Any], observed: dict[str, Any]) -> list[str]:
    failures: list[str] = []

    if "expected_decision" in expected_case and observed.get("decision") != expected_case["expected_decision"]:
        failures.append(
            f"Decision mismatch. expected={expected_case['expected_decision']} observed={observed.get('decision')}"
        )

    if "expected_reason" in expected_case and observed.get("reason") != expected_case["expected_reason"]:
        failures.append(
            f"Reason mismatch. expected={expected_case['expected_reason']} observed={observed.get('reason')}"
        )

    expected_redactions = expected_case.get("expected_redactions", [])
    observed_redactions = set(observed.get("redactions", []))
    for redaction in expected_redactions:
        if redaction not in observed_redactions:
            failures.append(f"Missing expected redaction token: {redaction}")

    required_sources = expected_case.get("required_sources", [])
    observed_sources = set(observed.get("source_urls", []))
    for source in required_sources:
        if source not in observed_sources:
            failures.append(f"Missing required source: {source}")

    forbidden_content = [item.lower() for item in expected_case.get("forbidden_content", [])]
    answer_text = (observed.get("answer_text") or "").lower()
    for content in forbidden_content:
        if content in answer_text:
            failures.append(f"Forbidden content found in answer text: {content}")

    return failures


def _contains_subsequence(sequence: list[str], expected_subsequence: list[str]) -> bool:
    if not expected_subsequence:
        return True

    target_index = 0
    for item in sequence:
        if item == expected_subsequence[target_index]:
            target_index += 1
            if target_index == len(expected_subsequence):
                return True
    return False


def _load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("cases", [])


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic skill eval harness")
    parser.add_argument("--skill", help="Optional skill id filter")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args()

    summary = run_eval_harness(skill_filter=args.skill)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Eval results: {summary['passed']}/{summary['total']} passed")
        for result in summary["results"]:
            state = "PASS" if result["passed"] else "FAIL"
            print(f"- [{state}] {result['skill']}::{result['case_id']}")
            for failure in result["failures"]:
                print(f"    - {failure}")

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
