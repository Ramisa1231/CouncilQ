from __future__ import annotations

from typing import Protocol


class Reranker(Protocol):
    def rerank(self, query: str, candidates: list[dict], *, limit: int) -> list[dict]:
        ...


class ScoreReranker:
    """Deterministic fallback reranker that sorts by existing score fields."""

    def rerank(self, query: str, candidates: list[dict], *, limit: int) -> list[dict]:
        ranked = sorted(
            candidates,
            key=lambda candidate: (
                float(candidate.get("rerank_score", candidate.get("rrf_score", candidate.get("score", 0.0)))),
                float(candidate.get("retrieval_score", 0.0)),
                float(candidate.get("lexical_score", 0.0)),
            ),
            reverse=True,
        )[:limit]

        for rank, candidate in enumerate(ranked, start=1):
            candidate.setdefault("rerank_score", candidate.get("rrf_score", candidate.get("score", 0.0)))
            candidate["rerank_rank"] = rank

        return ranked
