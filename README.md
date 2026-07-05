# CouncilQ

CouncilQ is a single-agent, RAG-based AI assistant for the City of Adelaide.

It follows the attached whitepaper guidance:

- Spec-driven development before code.
- One general-purpose agent with modular skills.
- Evaluation-first skill development.
- MCP/tool interoperability where appropriate.
- Central policy checks for prompt injection, PII, and unsafe tool calls.
- Trusted-source retrieval from City of Adelaide and government sources.

## Current Status

This repository currently contains the project foundation:

- Product specs.
- Requirements and user stories.
- Evaluation plan.
- First skill scaffold: `waste_and_recycling`.
- Central policy documents and policy evals.

No production agent implementation has been added yet. That is intentional: CouncilQ requires specs and evals before code.

## Project Structure

CouncilQ is a project wrapper around a Day 3 Agent Skills library. Each reusable capability must be a skill folder using the canonical Day 3 structure.

```text
CouncilQ/
├── AGENTS.md
├── .agents-cli-spec.md
├── specs/
├── skills/
│   ├── README.md
│   ├── waste_and_recycling/
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   ├── references/
│   │   ├── assets/
│   │   ├── tests/
│   │   └── evals/
│   └── policy_guard/
│       ├── SKILL.md
│       ├── scripts/
│       ├── references/
│       ├── assets/
│       ├── tests/
│       └── evals/
├── policies/
├── tests/
├── evals/
└── app/
```

Canonical Day 3 skill structure:

```text
skill_name/
├── SKILL.md
├── scripts/
├── references/
├── assets/
├── ...
```

## Next Build Step

Create the deterministic foundation for:

- Source allowlisting.
- PII masking.
- Policy decision types.
- RAG ingestion metadata.

Then scaffold the ADK prototype and wire the first read-only retrieval flow.
