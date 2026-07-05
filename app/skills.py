from __future__ import annotations

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"


def _read_frontmatter(skill_md: Path) -> dict[str, Any]:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    _, frontmatter, _ = text.split("---", 2)
    metadata: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in frontmatter.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line.startswith(" ") and current_key:
            metadata[current_key] = f"{metadata.get(current_key, '')}\n{line.strip()}".strip()
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            current_key = key.strip()
            metadata[current_key] = value.strip().strip('"')
    return metadata


def load_skill_registry() -> dict[str, Any]:
    """Load CouncilQ skill metadata from Day 3 skill folders."""
    skills: dict[str, Any] = {}
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        metadata = _read_frontmatter(skill_md)
        skills[skill_dir.name] = {
            "path": str(skill_dir.relative_to(ROOT)),
            "name": metadata.get("name", skill_dir.name),
            "description": metadata.get("description", ""),
            "version": metadata.get("version", ""),
            "has_evals": all(
                (skill_dir / "evals" / filename).exists()
                for filename in ["input.json", "expected_tools.json", "expected_output.json"]
            ),
            "has_day3_folders": all(
                (skill_dir / folder).exists()
                for folder in ["scripts", "references", "assets"]
            ),
        }
    return {"skills": skills}

