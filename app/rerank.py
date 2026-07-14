from __future__ import annotations

from typing import Protocol


class Reranker(Protocol):
    def rerank(self, query: str, candidates: list[dict], *, limit: int) -> list[dict]:
        ...


class ScoreReranker:
    """Deterministic fallback reranker that sorts by existing score fields."""

    def rerank(self, query: str, candidates: list[dict], *, limit: int) -> list[dict]:
        return sorted(
            candidates,
            key=lambda candidate: float(candidate.get("score", candidate.get("rrf_score", 0.0))),
            reverse=True,
        )[:limit]
