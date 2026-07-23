from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.grounding import validate_retrieval_grounding
from app.retrieval import answer_question


ROOT = Path(__file__).resolve().parents[1]
ANSWER_CASES_PATH = ROOT / "evals" / "answer_cases.json"


@dataclass
class CaseResult:
    case_id: str
    passed: bool
    failures: list[str]
    observed: dict[str, Any]


def run_eval_harness(case_filter: str | None = None) -> dict[str, Any]:
    cases = _load_cases(ANSWER_CASES_PATH)
    if case_filter:
        cases = [case for case in cases if case["id"] == case_filter]

    results = [_run_case(case) for case in cases]
    passed = sum(1 for result in results if result.passed)
    contract_metrics = _contract_metrics(cases, results)
    return {
        "scope": "checked-in deterministic answer-routing fixture",
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "contract_metrics": contract_metrics,
        "results": [
            {
                "case_id": result.case_id,
                "passed": result.passed,
                "failures": result.failures,
                "observed": result.observed,
            }
            for result in results
        ],
    }


def _contract_metrics(
    cases: list[dict[str, Any]],
    results: list[CaseResult],
) -> dict[str, Any]:
    routing_hits = 0
    policy_hits = 0
    policy_total = 0
    citation_hits = 0
    citation_total = 0
    required_hits = 0
    required_total = 0
    forbidden_hits = 0
    forbidden_total = 0

    for case, result in zip(cases, results, strict=True):
        observed = result.observed
        routing_hits += observed.get("status") == case.get("expected_status")

        expected_policy = case.get("expected_policy_decision")
        if expected_policy:
            policy_total += 1
            policy_hits += observed.get("policy", {}).get("decision") == expected_policy

        if case.get("expected_status") == "answered":
            citation_total += 1
            validated = validate_retrieval_grounding(
                {
                    "status": "answered",
                    "message": "",
                    "sources": observed.get("sources", []),
                }
            )
            citation_hits += validated.get("status") == "answered"

        answer_text = (observed.get("answer") or "").lower()
        for required in case.get("required_content", []):
            required_total += 1
            required_hits += required.lower() in answer_text
        for forbidden in case.get("forbidden_content", []):
            forbidden_total += 1
            forbidden_hits += forbidden.lower() not in answer_text

    return {
        "routing_accuracy": _ratio(routing_hits, len(cases)),
        "policy_decision_accuracy": _ratio(policy_hits, policy_total),
        "policy_labelled_cases": policy_total,
        "citation_validity_rate": _ratio(citation_hits, citation_total),
        "answered_cases": citation_total,
        "required_content_coverage": _ratio(required_hits, required_total),
        "required_content_assertions": required_total,
        "forbidden_content_avoidance": _ratio(forbidden_hits, forbidden_total),
        "forbidden_content_assertions": forbidden_total,
    }


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _run_case(case: dict[str, Any]) -> CaseResult:
    observed = answer_question(
        case["question"],
        council=case.get("council", "City of Adelaide"),
        fetch_live_pages=False,
    )
    failures = _validate_case(case, observed)
    return CaseResult(case["id"], not failures, failures, observed)


def _validate_case(case: dict[str, Any], observed: dict[str, Any]) -> list[str]:
    failures: list[str] = []

    if observed.get("status") != case.get("expected_status"):
        failures.append(
            f"Status mismatch. expected={case.get('expected_status')} observed={observed.get('status')}"
        )

    expected_policy_decision = case.get("expected_policy_decision")
    if expected_policy_decision and observed.get("policy", {}).get("decision") != expected_policy_decision:
        failures.append(
            f"Policy decision mismatch. expected={expected_policy_decision} observed={observed.get('policy', {}).get('decision')}"
        )

    observed_sources = {source.get("url") for source in observed.get("sources", [])}
    for source_url in case.get("required_sources", []):
        if source_url not in observed_sources:
            failures.append(f"Missing required source: {source_url}")

    for source_url in case.get("forbidden_sources", []):
        if source_url in observed_sources:
            failures.append(f"Forbidden source returned: {source_url}")

    answer_text = (observed.get("answer") or "").lower()
    for text in case.get("required_content", []):
        if text.lower() not in answer_text:
            failures.append(f"Missing required content: {text}")

    for text in case.get("forbidden_content", []):
        if text.lower() in answer_text:
            failures.append(f"Forbidden content found: {text}")

    return failures


def _load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("cases", [])


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic CouncilQ answer evals")
    parser.add_argument("--case", help="Optional answer case id filter")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args()

    summary = run_eval_harness(case_filter=args.case)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Eval results: {summary['passed']}/{summary['total']} passed")
        metrics = summary["contract_metrics"]
        print(
            "Contract metrics: "
            f"routing={metrics['routing_accuracy']:.3f} "
            f"citation_validity={metrics['citation_validity_rate']:.3f}"
        )
        for result in summary["results"]:
            state = "PASS" if result["passed"] else "FAIL"
            print(f"- [{state}] {result['case_id']}")
            for failure in result["failures"]:
                print(f"    - {failure}")

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
