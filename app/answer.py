from __future__ import annotations


def format_answer(message: str, sources: list[dict[str, str]]) -> str:
    source_lines = "\n".join(f"- {source['title']}: {source['url']}" for source in sources)
    return (
        f"{message}\n\n"
        "Use the linked City of Adelaide source to confirm the latest details before acting.\n\n"
        f"Sources:\n{source_lines}"
    )
