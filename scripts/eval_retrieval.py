from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from app.rag import search_council_sources


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES_PATH = ROOT / "evals" / "retrieval_cases.json"


@dataclass(frozen=True)
class RetrievalItem:
    source_url: str
    title: str = ""
    page: str | None = None
    chunk_id: str | None = None


def load_retrieval_cases(path: Path = DEFAULT_CASES_PATH) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    validate_retrieval_cases(cases)
    return cases


def retrieve_for_case(query: str, *, k: int) -> list[RetrievalItem]:
    result = search_council_sources(query, fetch_live_pages=False)
    sources = result.get("sources", [])
    return [
        RetrievalItem(
            source_url=str(source.get("url", "")),
            title=str(source.get("title", "")),
            page=str(source["page"]) if "page" in source else None,
            chunk_id=str(source["chunk_id"]) if "chunk_id" in source else None,
        )
        for source in sources[:k]
    ]


def evaluate_retrieval_cases(cases: list[dict[str, Any]], *, k: int = 5) -> dict[str, Any]:
    if k <= 0:
        raise ValueError("k must be greater than 0")
    validate_retrieval_cases(cases)

    results: list[dict[str, Any]] = []
    for case in cases:
        retrieved = retrieve_for_case(case["query"], k=k)
        relevant_ids = _expected_relevance_ids(case)
        forbidden_urls = {_normalize_url(url) for url in case.get("forbidden_source_urls", [])}
        retrieved_id_sets = [_item_relevance_ids(item) for item in retrieved]
        retrieved_urls = [item.source_url for item in retrieved]

        forbidden_hits = [
            url for url in retrieved_urls if _normalize_url(url) in forbidden_urls
        ]
        metrics = calculate_case_metrics(retrieved_id_sets, relevant_ids, k=k)
        results.append(
            {
                "id": case["id"],
                "query": case["query"],
                "retrieved": [item.__dict__ for item in retrieved],
                "expected": sorted(relevant_ids),
                "forbidden_hits": forbidden_hits,
                "metrics": metrics,
                "passed": metrics[f"recall@{k}"] == 1.0 and not forbidden_hits,
            }
        )

    aggregate = aggregate_metrics([result["metrics"] for result in results], k=k)
    return {
        "k": k,
        "total": len(results),
        "passed": sum(1 for result in results if result["passed"]),
        "failed": sum(1 for result in results if not result["passed"]),
        "metrics": aggregate,
        "results": results,
    }


def validate_retrieval_cases(cases: list[dict[str, Any]]) -> None:
    if not isinstance(cases, list):
        raise ValueError("retrieval cases payload must contain a list of cases")

    for index, case in enumerate(cases):
        label = case.get("id", f"case[{index}]") if isinstance(case, dict) else f"case[{index}]"
        if not isinstance(case, dict):
            raise ValueError(f"{label}: case must be an object")
        for field in ["id", "query"]:
            if not isinstance(case.get(field), str) or not case[field].strip():
                raise ValueError(f"{label}: missing required string field '{field}'")

        expected_fields = ["expected_source_urls", "expected_pages", "expected_chunk_ids"]
        if not any(case.get(field) for field in expected_fields):
            raise ValueError(
                f"{label}: at least one of expected_source_urls, expected_pages, or expected_chunk_ids is required"
            )

        _validate_string_list(case, "expected_source_urls", label)
        _validate_string_list(case, "expected_chunk_ids", label)
        _validate_string_list(case, "forbidden_source_urls", label)

        expected_pages = case.get("expected_pages", [])
        if expected_pages is None:
            continue
        if not isinstance(expected_pages, list):
            raise ValueError(f"{label}: expected_pages must be a list")
        for page_index, page in enumerate(expected_pages):
            if not isinstance(page, dict):
                raise ValueError(f"{label}: expected_pages[{page_index}] must be an object")
            if not isinstance(page.get("source_url"), str) or not page["source_url"].strip():
                raise ValueError(f"{label}: expected_pages[{page_index}].source_url is required")
            if "page" not in page:
                raise ValueError(f"{label}: expected_pages[{page_index}].page is required")


def calculate_case_metrics(
    retrieved_ids: list[str] | list[set[str]],
    relevant_ids: set[str],
    *,
    k: int,
) -> dict[str, float]:
    if k <= 0:
        raise ValueError("k must be greater than 0")

    top_k = [_coerce_id_set(item) for item in retrieved_ids[:k]]
    if not relevant_ids:
        return {f"recall@{k}": 1.0, f"mrr@{k}": 0.0, f"ndcg@{k}": 0.0}

    hits = set()
    for identifiers in top_k:
        hits.update(identifiers & relevant_ids)
    recall = len(set(hits)) / len(relevant_ids)
    mrr = _reciprocal_rank(top_k, relevant_ids)
    ndcg = _ndcg(top_k, relevant_ids)
    return {f"recall@{k}": recall, f"mrr@{k}": mrr, f"ndcg@{k}": ndcg}


def aggregate_metrics(case_metrics: list[dict[str, float]], *, k: int) -> dict[str, float]:
    if not case_metrics:
        return {f"recall@{k}": 0.0, f"mrr@{k}": 0.0, f"ndcg@{k}": 0.0}

    keys = [f"recall@{k}", f"mrr@{k}", f"ndcg@{k}"]
    return {
        key: sum(metrics[key] for metrics in case_metrics) / len(case_metrics)
        for key in keys
    }


def _expected_relevance_ids(case: dict[str, Any]) -> set[str]:
    expected: set[str] = set()
    for url in case.get("expected_source_urls", []):
        expected.add(_normalize_url(str(url)))
    for page in case.get("expected_pages", []):
        expected.add(f"{_normalize_url(str(page['source_url']))}#page={page['page']}")
    for chunk_id in case.get("expected_chunk_ids", []):
        expected.add(f"chunk:{chunk_id}")
    return expected


def _item_relevance_ids(item: RetrievalItem) -> set[str]:
    ids = {_normalize_url(item.source_url)}
    if item.page:
        ids.add(f"{_normalize_url(item.source_url)}#page={item.page}")
    if item.chunk_id:
        ids.add(f"chunk:{item.chunk_id}")
    return ids


def _reciprocal_rank(retrieved_ids: list[set[str]], relevant_ids: set[str]) -> float:
    for index, identifiers in enumerate(retrieved_ids, start=1):
        if identifiers & relevant_ids:
            return 1.0 / index
    return 0.0


def _ndcg(retrieved_ids: list[set[str]], relevant_ids: set[str]) -> float:
    """Return binary-relevance nDCG for the retrieved identifier sets."""
    dcg = 0.0
    for index, identifiers in enumerate(retrieved_ids, start=1):
        if identifiers & relevant_ids:
            dcg += 1.0 / _log2(index + 1)

    ideal_hits = min(len(retrieved_ids), len(relevant_ids))
    idcg = sum(1.0 / _log2(index + 1) for index in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def _log2(value: int) -> float:
    import math

    return math.log(value, 2)


def _coerce_id_set(item: str | set[str]) -> set[str]:
    if isinstance(item, set):
        return item
    return {item}


def _validate_string_list(case: dict[str, Any], field: str, label: str) -> None:
    values = case.get(field, [])
    if values is None:
        return
    if not isinstance(values, list):
        raise ValueError(f"{label}: {field} must be a list")
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label}: {field}[{index}] must be a non-empty string")


def _normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    path = parsed.path
    if path != "/":
        path = path.rstrip("/")
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            "",
            "",
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate CouncilQ retrieval quality.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--fail-under",
        type=float,
        default=None,
        help="Optional minimum Recall@k threshold. Without this flag, metric failures do not change the exit code.",
    )
    args = parser.parse_args()
    if args.k <= 0:
        parser.error("--k must be greater than 0")

    summary = evaluate_retrieval_cases(load_retrieval_cases(args.cases), k=args.k)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        metrics = summary["metrics"]
        print(f"Retrieval eval: {summary['passed']}/{summary['total']} cases passed")
        print(
            f"Recall@{args.k}: {metrics[f'recall@{args.k}']:.3f} | "
            f"MRR@{args.k}: {metrics[f'mrr@{args.k}']:.3f} | "
            f"nDCG@{args.k}: {metrics[f'ndcg@{args.k}']:.3f}"
        )
        for result in summary["results"]:
            state = "PASS" if result["passed"] else "FAIL"
            print(f"- [{state}] {result['id']}")
            for forbidden_hit in result["forbidden_hits"]:
                print(f"    forbidden source retrieved: {forbidden_hit}")

    if args.fail_under is not None and summary["metrics"][f"recall@{args.k}"] < args.fail_under:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
