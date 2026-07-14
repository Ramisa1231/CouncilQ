from __future__ import annotations

from typing import Any

from .retrieval import answer_question


def answer_council_question(
    question: str,
    council: str = "City of Adelaide",
    *,
    fetch_live_pages: bool = True,
) -> dict[str, Any]:
    """Answer a City of Adelaide council question with the single RAG pipeline."""
    return answer_question(question, council=council, fetch_live_pages=fetch_live_pages)
