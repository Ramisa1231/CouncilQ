from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.policy import check_request


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES_PATH = ROOT / "evals" / "policy_cases.json"


def run_policy_harness(cases_path: Path = DEFAULT_CASES_PATH) -> dict[str, Any]:
    cases = _load_cases(cases_path)
    results = [_evaluate_case(case) for case in cases]
    injection_pairs = [
        (bool(case["expected_injection"]), bool(result["observed_injection"]))
        for case, result in zip(cases, results, strict=True)
    ]
    pii_pairs = [
        (bool(case.get("expected_pii_labels")), bool(result["observed_pii_labels"]))
        for case, result in zip(cases, results, strict=True)
    ]
    passed = sum(1 for result in results if result["passed"])
    return {
        "scope": "checked-in deterministic policy fixture",
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "prompt_injection": _classification_metrics(injection_pairs),
        "pii_detection": _classification_metrics(pii_pairs),
        "results": results,
    }


def _evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    observed = check_request(
        text=case["input"],
        requested_tool="rag.search",
        role="public_user",
        environment="evaluation",
    )
    observed_injection = bool(observed["detected_prompt_injection"])
    expected_labels = set(case.get("expected_pii_labels", []))
    observed_labels = set(observed.get("redactions", []))
    failures: list[str] = []
    if observed["decision"] != case["expected_decision"]:
        failures.append(
            f"decision expected={case['expected_decision']} observed={observed['decision']}"
        )
    if observed_injection != case["expected_injection"]:
        failures.append(
            f"injection expected={case['expected_injection']} observed={observed_injection}"
        )
    if observed_labels != expected_labels:
        failures.append(
            f"pii_labels expected={sorted(expected_labels)} observed={sorted(observed_labels)}"
        )
    return {
        "id": case["id"],
        "passed": not failures,
        "failures": failures,
        "observed_decision": observed["decision"],
        "observed_injection": observed_injection,
        "observed_pii_labels": sorted(observed_labels),
    }


def _classification_metrics(pairs: list[tuple[bool, bool]]) -> dict[str, Any]:
    true_positive = sum(expected and observed for expected, observed in pairs)
    true_negative = sum(not expected and not observed for expected, observed in pairs)
    false_positive = sum(not expected and observed for expected, observed in pairs)
    false_negative = sum(expected and not observed for expected, observed in pairs)
    precision = _safe_ratio(true_positive, true_positive + false_positive)
    recall = _safe_ratio(true_positive, true_positive + false_negative)
    false_positive_rate = _safe_ratio(false_positive, false_positive + true_negative)
    return {
        "true_positive": true_positive,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": precision,
        "recall": recall,
        "false_positive_rate": false_positive_rate,
    }


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    if not cases:
        raise ValueError(f"No policy cases found in {path}")
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic CouncilQ policy evals")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    summary = run_policy_harness(args.cases)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Policy eval: {summary['passed']}/{summary['total']} cases passed")
        for label in ("prompt_injection", "pii_detection"):
            metrics = summary[label]
            print(
                f"{label}: precision={metrics['precision']:.3f} "
                f"recall={metrics['recall']:.3f} "
                f"false_positive_rate={metrics['false_positive_rate']:.3f}"
            )
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
