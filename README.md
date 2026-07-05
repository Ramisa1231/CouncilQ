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
- First service skill scaffold: `waste_and_recycling`.
- First governance skill scaffold: `policy_guard`.
- Google ADK entry point in `agent.py`, backed by implementation files in `app/`.

The current implementation is a read-only MVP foundation. It loads the skill registry, applies deterministic policy checks, and returns trusted City of Adelaide source links for the first waste-and-recycling cases.

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
│   │   ├── evals/
│   │   │   ├── input.json
│   │   │   ├── expected_tools.json
│   │   │   └── expected_output.json
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   ├── references/
│   │   ├── assets/
│   │   └── tests/
│   └── policy_guard/
│       ├── evals/
│       │   ├── input.json
│       │   ├── expected_tools.json
│       │   └── expected_output.json
│       ├── SKILL.md
│       ├── scripts/
│       ├── references/
│       ├── assets/
│       └── tests/
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

CouncilQ skill creation order:

1. Choose one skill.
2. Write `evals/input.json`.
3. Write `evals/expected_tools.json`.
4. Write `evals/expected_output.json`.
5. Then write `SKILL.md` using the Day 3 page 46 template.
6. Then add `scripts/`, `references/`, and `assets/`.
7. Run evals before accepting the skill.

## Next Build Step

Install project dependencies in your preferred Python environment, then run deterministic tests:

```powershell
pip install -e ".[dev]"
pytest
```

Run with ADK tooling once the environment is configured:

```powershell
cd C:\Users\ramif\Documents\Codex\2026-07-05\d
adk web
```

Then select `CouncilQ` in the ADK web UI.
