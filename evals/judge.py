from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.retrieval import answer_question


ROOT = Path(__file__).resolve().parents[1]
JUDGE_CASES_PATH = ROOT / "evals" / "judge_cases.json"

OFFICIAL_SOURCE_DOMAINS = {
    "cityofadelaide.com.au",
    "www.cityofadelaide.com.au",
    "whichbin.sa.gov.au",
    "www.whichbin.sa.gov.au",
    "d31atr86jnqrq2.cloudfront.net",
}


@dataclass(frozen=True)
class JudgeResult:
    name: str
    passed: bool
    failures: list[str]


def run_judge_harness(case_filter: str | None = None) -> dict[str, Any]:
    cases = _load_cases(JUDGE_CASES_PATH)
    if case_filter:
        cases = [case for case in cases if case["id"] == case_filter]

    results = [_run_case(case) for case in cases]
    passed = sum(1 for result in results if result["passed"])
    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }


def judge_response(case: dict[str, Any], observed: dict[str, Any]) -> list[JudgeResult]:
    """Run deterministic LlamaIndex-style response judges.

    LlamaIndex describes response evaluation across dimensions such as
    faithfulness, context relevancy, answer relevancy, and guideline adherence.
    CouncilQ keeps these judges deterministic so CI does not need an LLM key.
    """
    return [
        _judge_faithfulness(case, observed),
        _judge_context_relevancy(case, observed),
        _judge_answer_relevancy(case, observed),
        _judge_guideline_adherence(case, observed),
    ]


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    observed = answer_question(
        case["question"],
        council=case.get("council", "City of Adelaide"),
        fetch_live_pages=False,
    )
    judge_results = judge_response(case, observed)
    failures = [
        f"{result.name}: {failure}"
        for result in judge_results
        for failure in result.failures
    ]
    return {
        "case_id": case["id"],
        "passed": not failures,
        "failures": failures,
        "judges": [
            {
                "name": result.name,
                "passed": result.passed,
                "failures": result.failures,
            }
            for result in judge_results
        ],
        "observed": observed,
    }


def _judge_faithfulness(case: dict[str, Any], observed: dict[str, Any]) -> JudgeResult:
    failures: list[str] = []
    answer = _answer_text(observed)
    status = observed.get("status")

    if status != case.get("expected_status"):
        failures.append(
            f"expected status {case.get('expected_status')}, observed {status}"
        )

    if status == "answered" and not observed.get("sources"):
        failures.append("answered response has no citations")

    for forbidden in case.get("answer_must_not_include", []):
        if forbidden.lower() in answer:
            failures.append(f"answer contains unsupported/forbidden text: {forbidden}")

    return JudgeResult("faithfulness", not failures, failures)


def _judge_context_relevancy(case: dict[str, Any], observed: dict[str, Any]) -> JudgeResult:
    failures: list[str] = []
    observed_sources = {_normalize_url(source.get("url", "")) for source in observed.get("sources", [])}

    for source_url in case.get("required_sources", []):
        normalized = _normalize_url(source_url)
        if normalized not in observed_sources:
            failures.append(f"missing relevant source: {source_url}")

    for source_url in case.get("forbidden_sources", []):
        normalized = _normalize_url(source_url)
        if normalized in observed_sources:
            failures.append(f"irrelevant/forbidden source returned: {source_url}")

    return JudgeResult("context_relevancy", not failures, failures)


def _judge_answer_relevancy(case: dict[str, Any], observed: dict[str, Any]) -> JudgeResult:
    failures: list[str] = []
    answer = _answer_text(observed)

    for required in case.get("answer_must_include", []):
        if required.lower() not in answer:
            failures.append(f"answer does not include required relevant text: {required}")

    if not answer:
        failures.append("answer text is empty")

    return JudgeResult("answer_relevancy", not failures, failures)


def _judge_guideline_adherence(case: dict[str, Any], observed: dict[str, Any]) -> JudgeResult:
    failures: list[str] = []
    answer = _answer_text(observed)
    sources = observed.get("sources", [])
    guidelines = set(case.get("guidelines", []))

    if "cite_official_sources" in guidelines:
        for source in sources:
            if not _is_official_source(source.get("url", "")):
                failures.append(f"unofficial source cited: {source.get('url', '')}")

    if "ask_for_address_before_collection_day" in guidelines:
        if observed.get("status") != "clarification_required":
            failures.append("collection-day query did not route to clarification")
        if "address" not in answer:
            failures.append("collection-day clarification did not ask for address")

    if "sanitize_prompt_injection" in guidelines:
        if observed.get("policy", {}).get("decision") != case.get("expected_policy_decision"):
            failures.append("prompt-injection policy decision did not match expectation")
        if "ignore previous instructions" in answer:
            failures.append("prompt-injection text leaked into answer")

    if "stay_within_city_of_adelaide_scope" in guidelines:
        if observed.get("status") != "clarification_required":
            failures.append("out-of-scope council query did not route to clarification")
        if "city of adelaide" not in answer:
            failures.append("scope clarification did not mention City of Adelaide")

    if "avoid_forbidden_sources" in guidelines:
        observed_sources = {_normalize_url(source.get("url", "")) for source in sources}
        for source_url in case.get("forbidden_sources", []):
            if _normalize_url(source_url) in observed_sources:
                failures.append(f"forbidden source cited: {source_url}")

    return JudgeResult("guideline_adherence", not failures, failures)


def _load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("cases", [])


def _answer_text(observed: dict[str, Any]) -> str:
    return str(observed.get("answer", "")).lower()


def _is_official_source(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in OFFICIAL_SOURCE_DOMAINS


def _normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    path = parsed.path
    if path != "/":
        path = path.rstrip("/")
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic LlamaIndex-style CouncilQ judge evals")
    parser.add_argument("--case", help="Optional judge case id filter")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args()

    summary = run_judge_harness(case_filter=args.case)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Judge eval results: {summary['passed']}/{summary['total']} passed")
        for result in summary["results"]:
            state = "PASS" if result["passed"] else "FAIL"
            print(f"- [{state}] {result['case_id']}")
            for failure in result["failures"]:
                print(f"    - {failure}")

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
