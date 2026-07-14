from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    return payload.get("cases", [])


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
    results: list[dict[str, Any]] = []
    for case in cases:
        retrieved = retrieve_for_case(case["query"], k=k)
        relevant_ids = _expected_relevance_ids(case)
        forbidden_urls = set(case.get("forbidden_source_urls", []))
        retrieved_ids = [_item_relevance_id(item) for item in retrieved]
        retrieved_urls = [item.source_url for item in retrieved]

        forbidden_hits = [url for url in retrieved_urls if url in forbidden_urls]
        metrics = calculate_case_metrics(retrieved_ids, relevant_ids, k=k)
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


def calculate_case_metrics(retrieved_ids: list[str], relevant_ids: set[str], *, k: int) -> dict[str, float]:
    top_k = retrieved_ids[:k]
    if not relevant_ids:
        return {f"recall@{k}": 1.0, f"mrr@{k}": 0.0, f"ndcg@{k}": 0.0}

    hits = [identifier for identifier in top_k if identifier in relevant_ids]
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
        expected.add(str(url))
    for page in case.get("expected_pages", []):
        expected.add(f"{page['source_url']}#page={page['page']}")
    for chunk_id in case.get("expected_chunk_ids", []):
        expected.add(f"chunk:{chunk_id}")
    return expected


def _item_relevance_id(item: RetrievalItem) -> str:
    if item.chunk_id:
        return f"chunk:{item.chunk_id}"
    if item.page:
        return f"{item.source_url}#page={item.page}"
    return item.source_url


def _reciprocal_rank(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    for index, identifier in enumerate(retrieved_ids, start=1):
        if identifier in relevant_ids:
            return 1.0 / index
    return 0.0


def _ndcg(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    dcg = 0.0
    for index, identifier in enumerate(retrieved_ids, start=1):
        if identifier in relevant_ids:
            dcg += 1.0 / _log2(index + 1)

    ideal_hits = min(len(retrieved_ids), len(relevant_ids))
    idcg = sum(1.0 / _log2(index + 1) for index in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def _log2(value: int) -> float:
    import math

    return math.log(value, 2)


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
