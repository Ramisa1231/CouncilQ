# Requirements

## Functional Requirements

- FR1: The assistant shall answer City of Adelaide council service questions using trusted retrieved sources.
- FR2: The assistant shall cite source URLs in user-facing answers.
- FR3: The assistant shall ask for clarification when location, date, council area, address, or service type is required.
- FR4: The assistant shall route waste and recycling questions to the `waste_and_recycling` skill.
- FR5: The assistant shall run policy checks before external tool calls.
- FR6: The assistant shall block prompt-injection attempts found in user input or retrieved content.
- FR7: The assistant shall mask PII in logs and internal policy records.
- FR8: The assistant shall require explicit approval before high-risk actions.

## Non-Functional Requirements

- NFR1: The assistant shall follow spec-driven development.
- NFR2: Each skill shall be evaluated before implementation acceptance.
- NFR3: Each skill shall use the Day 3 folder structure: `SKILL.md`, `scripts/`, `references/`, `assets/`, `tests/`, and `evals/`.
- NFR4: The system shall remain a single-agent design unless a documented architecture decision says otherwise.
- NFR5: Retrieval sources shall be allowlisted.
- NFR6: Behavioral quality shall be tested with evals rather than pytest string assertions.

## Source Requirements

- SR1: City of Adelaide pages are primary trusted sources.
- SR2: Linked state or government services may be trusted only when source provenance is documented.
- SR3: Time-sensitive alerts must be retrieved at answer time.
- SR4: The assistant must disclose when retrieved information is insufficient.

