from evals.harness import run_eval_harness


def test_eval_harness_runs_all_current_answer_contracts():
    summary = run_eval_harness()

    assert summary["total"] == 6
    assert summary["failed"] == 0
