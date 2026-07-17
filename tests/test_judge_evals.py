from evals.judge import judge_response, run_judge_harness


def test_judge_harness_runs_current_llamaindex_style_cases():
    summary = run_judge_harness()

    assert summary["total"] == 4
    assert summary["failed"] == 0
    assert all(len(result["judges"]) == 4 for result in summary["results"])


def test_judge_response_reports_all_four_dimensions():
    case = {
        "id": "sample",
        "question": "When are my bins collected?",
        "expected_status": "clarification_required",
        "required_sources": ["https://www.cityofadelaide.com.au/resident/recycling-waste/bin-collection-day-checker/"],
        "answer_must_include": ["address"],
        "answer_must_not_include": ["Monday"],
        "guidelines": ["ask_for_address_before_collection_day", "cite_official_sources"],
    }
    observed = {
        "status": "clarification_required",
        "answer": "Please provide the City of Adelaide property address.",
        "policy": {"decision": "allow"},
        "sources": [
            {
                "title": "City of Adelaide bin collection day checker",
                "url": "https://www.cityofadelaide.com.au/resident/recycling-waste/bin-collection-day-checker/",
            }
        ],
    }

    results = judge_response(case, observed)

    assert [result.name for result in results] == [
        "faithfulness",
        "context_relevancy",
        "answer_relevancy",
        "guideline_adherence",
    ]
    assert all(result.passed for result in results)


def test_judge_response_rejects_unfaithful_or_unofficial_answer():
    case = {
        "id": "bad",
        "question": "When are my bins collected?",
        "expected_status": "clarification_required",
        "required_sources": ["https://www.cityofadelaide.com.au/resident/recycling-waste/bin-collection-day-checker/"],
        "answer_must_include": ["address"],
        "answer_must_not_include": ["Monday"],
        "guidelines": ["ask_for_address_before_collection_day", "cite_official_sources"],
    }
    observed = {
        "status": "answered",
        "answer": "Your bins are collected Monday.",
        "policy": {"decision": "allow"},
        "sources": [{"title": "Unofficial", "url": "https://example.com/bin-days"}],
    }

    results = judge_response(case, observed)
    failures = [failure for result in results for failure in result.failures]

    assert any("expected status" in failure for failure in failures)
    assert any("unsupported/forbidden text" in failure for failure in failures)
    assert any("missing relevant source" in failure for failure in failures)
    assert any("unofficial source" in failure for failure in failures)
