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
- FR9: The assistant shall support an offline document-ingestion workflow for allowlisted City of Adelaide PDF documents.
- FR10: The assistant shall preserve document title, source URL, directory URL, local source file, page number, and content hash metadata for ingested PDF pages.
- FR11: The assistant shall cite retrieved PDF pages with document title, page number, and official source URL when answering from ingested documents.

## Non-Functional Requirements

- NFR1: The assistant shall follow spec-driven development.
- NFR2: Each skill shall be evaluated before implementation acceptance.
- NFR3: Each skill shall use the Day 3 folder structure: `SKILL.md`, `scripts/`, `references/`, `assets/`, `tests/`, and `evals/`.
- NFR4: The system shall remain a single-agent design unless a documented architecture decision says otherwise.
- NFR5: Retrieval sources shall be allowlisted.
- NFR6: Behavioral quality shall be tested with evals rather than pytest string assertions.
- NFR7: Downloaded documents and generated indexes shall be reusable across assistant requests instead of being recreated for every question.
- NFR8: Document ingestion shall be deterministic and testable without live network access.

## Source Requirements

- SR1: City of Adelaide pages are primary trusted sources.
- SR2: Linked state or government services may be trusted only when source provenance is documented.
- SR3: Time-sensitive alerts must be retrieved at answer time.
- SR4: The assistant must disclose when retrieved information is insufficient.
- SR5: City of Adelaide policy, strategy, operating guideline, and by-law PDFs may be used when discovered from an official City of Adelaide directory page or an explicitly allowlisted official URL.
- SR6: Ingested document records must keep enough provenance to distinguish the directory page from the direct PDF URL.

