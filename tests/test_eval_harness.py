from evals.harness import run_eval_harness


def test_eval_harness_runs_all_current_answer_contracts():
    summary = run_eval_harness()

    assert summary["total"] == 6
    assert summary["failed"] == 0
    assert summary["scope"] == "checked-in deterministic answer-routing fixture"
    assert summary["contract_metrics"] == {
        "routing_accuracy": 1.0,
        "policy_decision_accuracy": 1.0,
        "policy_labelled_cases": 1,
        "citation_validity_rate": 1.0,
        "answered_cases": 4,
        "required_content_coverage": 1.0,
        "required_content_assertions": 1,
        "forbidden_content_avoidance": 1.0,
        "forbidden_content_assertions": 6,
    }
