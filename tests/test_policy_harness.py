from evals.policy_harness import _classification_metrics, run_policy_harness


def test_classification_metrics_report_confusion_matrix():
    metrics = _classification_metrics(
        [(True, True), (True, False), (False, True), (False, False)]
    )

    assert metrics == {
        "true_positive": 1,
        "true_negative": 1,
        "false_positive": 1,
        "false_negative": 1,
        "precision": 0.5,
        "recall": 0.5,
        "false_positive_rate": 0.5,
    }


def test_checked_in_policy_fixture_passes():
    summary = run_policy_harness()

    assert summary["scope"] == "checked-in deterministic policy fixture"
    assert summary["total"] == 8
    assert summary["failed"] == 0
