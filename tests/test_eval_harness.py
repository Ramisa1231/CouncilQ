from evals.harness import run_eval_harness


def test_eval_harness_runs_all_current_skill_contracts():
    summary = run_eval_harness()

    assert summary["total"] == 9
    assert summary["failed"] == 0
