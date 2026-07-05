# Evaluation Plan

## Evaluation Principles

- Write evals before skill implementation.
- Use three JSON files per skill: `input.json`, `expected_tools.json`, and `expected_output.json`.
- Treat evals as the functional contract for a skill.
- Use pytest only for deterministic code behavior, not natural-language response quality.

## MVP Skill Evals

The `waste_and_recycling` skill must pass cases for:

- Supported waste question with enough context.
- Missing-address or missing-location clarification.
- Missed-bin report guidance without automatic submission.
- Hard-waste guidance with source citation.
- Which-bin redirect or source use.
- Prompt injection embedded in user text.
- Unsupported council or non-Adelaide request.

## Policy Evals

Policy evals must verify:

- Prompt injection is ignored or blocked.
- PII is masked.
- Unsafe tool calls are blocked.
- Human approval is requested for sensitive actions.
- Safe retrieval requests continue normally.

## Acceptance Criteria

- All JSON eval files are valid.
- Each expected output names the required behavior, source constraints, and refusal or clarification behavior where relevant.
- The first implementation must pass deterministic tests and behavior evals before new service skills are added.

