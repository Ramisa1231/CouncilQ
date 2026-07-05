from app.skills import load_skill_registry


def test_current_skills_have_evals_and_day3_folders():
    registry = load_skill_registry()["skills"]

    assert "waste_and_recycling" in registry
    assert "policy_guard" in registry
    for skill in registry.values():
        assert skill["has_evals"] is True
        assert skill["has_day3_folders"] is True

