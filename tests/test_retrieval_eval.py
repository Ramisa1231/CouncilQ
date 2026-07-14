import json

from scripts.eval_retrieval import (
    aggregate_metrics,
    calculate_case_metrics,
    evaluate_retrieval_cases,
    load_retrieval_cases,
)


def test_calculate_case_metrics_for_ranked_hits():
    metrics = calculate_case_metrics(
        ["irrelevant", "source-a", "source-b"],
        {"source-a", "source-b"},
        k=3,
    )

    assert metrics["recall@3"] == 1.0
    assert metrics["mrr@3"] == 0.5
    assert round(metrics["ndcg@3"], 3) == 0.693


def test_aggregate_metrics_averages_cases():
    metrics = aggregate_metrics(
        [
            {"recall@5": 1.0, "mrr@5": 1.0, "ndcg@5": 1.0},
            {"recall@5": 0.0, "mrr@5": 0.0, "ndcg@5": 0.0},
        ],
        k=5,
    )

    assert metrics == {"recall@5": 0.5, "mrr@5": 0.5, "ndcg@5": 0.5}


def test_load_retrieval_cases(tmp_path):
    path = tmp_path / "cases.json"
    path.write_text(
        json.dumps({"cases": [{"id": "case-1", "query": "privacy", "expected_source_urls": ["url"]}]}),
        encoding="utf-8",
    )

    cases = load_retrieval_cases(path)

    assert cases[0]["id"] == "case-1"


def test_evaluate_retrieval_cases_uses_current_retrieval():
    summary = evaluate_retrieval_cases(
        [
            {
                "id": "bin-collection",
                "query": "When are my bins collected?",
                "expected_source_urls": [
                    "https://www.cityofadelaide.com.au/resident/recycling-waste/bin-collection-day-checker/"
                ],
                "forbidden_source_urls": [],
            }
        ],
        k=5,
    )

    assert summary["total"] == 1
    assert summary["passed"] == 1
    assert summary["metrics"]["recall@5"] == 1.0
    assert summary["results"][0]["retrieved"][0]["source_url"].endswith("/bin-collection-day-checker/")


def test_forbidden_sources_fail_case_even_with_recall():
    summary = evaluate_retrieval_cases(
        [
            {
                "id": "forbidden",
                "query": "When are my bins collected?",
                "expected_source_urls": [
                    "https://www.cityofadelaide.com.au/resident/recycling-waste/bin-collection-day-checker/"
                ],
                "forbidden_source_urls": [
                    "https://www.cityofadelaide.com.au/resident/recycling-waste/bin-collection-day-checker/"
                ],
            }
        ],
        k=5,
    )

    assert summary["failed"] == 1
    assert summary["metrics"]["recall@5"] == 1.0
    assert summary["results"][0]["forbidden_hits"]
