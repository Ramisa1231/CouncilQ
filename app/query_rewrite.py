from __future__ import annotations


def rewrite_query(query: str) -> list[str]:
    """Return deterministic query variants for retrieval expansion."""
    normalized = " ".join(query.split())
    variants = [normalized]
    lowered = normalized.lower()

    replacements = {
        "hard rubbish": "hard waste",
        "bin": "waste collection service",
        "bins": "waste collection service",
        "privacy": "privacy policy personal information",
    }
    for source, replacement in replacements.items():
        if source in lowered:
            variants.append(lowered.replace(source, replacement))

    deduped: list[str] = []
    for variant in variants:
        if variant and variant not in deduped:
            deduped.append(variant)
    return deduped[:3]
