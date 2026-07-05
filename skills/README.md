# Skills

CouncilQ skills follow the Day 3 Agent Skills structure and an evaluation-first creation order.

## Mandatory Skill Creation Order

For every CouncilQ skill:

1. Choose one skill.
2. Write `evals/input.json`.
3. Write `evals/expected_tools.json`.
4. Write `evals/expected_output.json`.
5. Then write `SKILL.md` using the Day 3 page 46 template.
6. Then add `scripts/`, `references/`, and `assets/`.
7. Run evals before accepting the skill.

The three eval files are the skill contract. They must exist before `SKILL.md` is written.

Canonical skill folder:

```text
skill_name/
├── SKILL.md      # Required: YAML frontmatter + markdown instructions
├── scripts/      # Optional: executable helper scripts
├── references/   # Optional: supplementary context loaded as needed
├── assets/       # Optional: templates, schemas, policies, examples
├── ...           # Additional files or directories when justified
```

CouncilQ uses `evals/` as an additional folder because skills are evaluation-first. `tests/` may be added only for deterministic helper code.

## Current Skills

- `waste_and_recycling`
- `policy_guard`
