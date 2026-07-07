# Evals

This folder includes the runnable deterministic eval harness (`python -m evals.harness`).

Use evals for:

- Agent routing.
- Skill selection.
- Tool trajectories.
- Source grounding.
- Safety behavior.
- Refusal and clarification behavior.

Skill-specific eval contracts live under each skill folder in:

- `evals/input.json`
- `evals/expected_tools.json`
- `evals/expected_output.json`

The harness executes these contracts against the current deterministic MVP behavior.
