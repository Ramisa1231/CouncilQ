# Evaluation Plan

## Evaluation Principles

- Write evals before skill implementation.
- Use three JSON files per skill: `input.json`, `expected_tools.json`, and `expected_output.json`.
- Treat evals as the functional contract for a skill.
- Use pytest only for deterministic code behavior, not natural-language response quality.

## Required Skill Creation Order

For every CouncilQ skill:

1. Choose one skill.
2. Write `evals/input.json`.
3. Write `evals/expected_tools.json`.
4. Write `evals/expected_output.json`.
5. Then write `SKILL.md` using the Day 3 page 46 template.
6. Then add `scripts/`, `references/`, and `assets/`.
7. Run evals before accepting the skill.

## MVP Skill Evals

The `waste_and_recycling` skill must pass cases for:

- Supported waste question with enough context.
- Missing-address or missing-location clarification.
- Missed-bin report guidance without automatic submission.
- Hard-waste guidance with source citation.
- Which-bin redirect or source use.
- Prompt injection embedded in user text.
- Unsupported council or non-Adelaide request.

## Document Retrieval Evals

The document-ingestion and retrieval layer must pass cases for:

- Loading extracted PDF page JSON records with title, URL, page, and text metadata.
- Returning a relevant City of Adelaide PDF page for a policy-style question.
- Including the official PDF URL and page number in retrieved source metadata.
- Falling back to unsupported when no extracted document page matches the question.
- Rejecting or ignoring document records without trusted source URLs.

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
- Document-ingestion changes must include deterministic unit tests that do not require live website access.
