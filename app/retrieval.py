from __future__ import annotations

import re
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from .answer import format_answer
from .context_compression import compress_context
from .document_ingestion import TEXT_DIRECTORY, load_extracted_pages
from .grounding import validate_retrieval_grounding
from .policy import check_request
from .query_rewrite import rewrite_query
from .rerank import Reranker, ScoreReranker
from .telemetry import log_retrieval_event
from .vector_db import VECTOR_DB_FILE, load_vector_database, search_vector_database


EMPTY_LIVE_RETRIEVAL = {
    "attempted": False,
    "available": False,
    "note": "Live retrieval not attempted.",
    "pages": [],
}


def answer_question(
    question: str,
    council: str = "City of Adelaide",
    *,
    fetch_live_pages: bool = True,
) -> dict[str, Any]:
    """Run the single CouncilQ advanced RAG pipeline for a public question."""
    trace_id = str(uuid4())
    started_at = perf_counter()
    policy_decision = check_request(
        text=question,
        requested_tool="rag.search",
        role="public_user",
        environment="development",
    )

    if policy_decision["decision"] == "block":
        return _finalize_result({
            "status": "blocked",
            "policy": policy_decision,
            "answer": "I cannot help with that request because it violates CouncilQ safety policy.",
            "sources": [],
            "live_retrieval": EMPTY_LIVE_RETRIEVAL,
        }, trace_id=trace_id, started_at=started_at)

    safe_question = policy_decision["sanitized_input"]
    from .rag import mentions_outside_city_of_adelaide

    if council.lower() != "city of adelaide" or mentions_outside_city_of_adelaide(safe_question.lower()):
        return _finalize_result({
            "status": "clarification_required",
            "policy": policy_decision,
            "answer": "CouncilQ is currently scoped to the City of Adelaide. Please confirm the property or service is in the City of Adelaide council area before I continue.",
            "sources": [],
            "live_retrieval": EMPTY_LIVE_RETRIEVAL,
        }, trace_id=trace_id, started_at=started_at)

    retrieval = validate_retrieval_grounding(
        retrieve_documents(safe_question, fetch_live_pages=fetch_live_pages)
    )
    if retrieval["status"] == "clarification_required":
        return _finalize_result({
            "status": "clarification_required",
            "policy": policy_decision,
            "answer": retrieval["message"],
            "sources": retrieval["sources"],
            "live_retrieval": retrieval.get("live_retrieval", EMPTY_LIVE_RETRIEVAL),
        }, trace_id=trace_id, started_at=started_at)

    if not retrieval["sources"]:
        return _finalize_result({
            "status": "unsupported",
            "policy": policy_decision,
            "answer": "I could not find trusted City of Adelaide source material for that question yet.",
            "sources": [],
            "live_retrieval": retrieval.get("live_retrieval", EMPTY_LIVE_RETRIEVAL),
        }, trace_id=trace_id, started_at=started_at)

    answer = format_answer(retrieval["message"], retrieval["sources"])
    return _finalize_result({
        "status": "answered",
        "policy": policy_decision,
        "answer": answer,
        "sources": retrieval["sources"],
        "live_retrieval": retrieval.get("live_retrieval", EMPTY_LIVE_RETRIEVAL),
    }, trace_id=trace_id, started_at=started_at)


def _finalize_result(
    result: dict[str, Any],
    *,
    trace_id: str,
    started_at: float,
) -> dict[str, Any]:
    result["trace_id"] = trace_id
    log_retrieval_event(
        trace_id=trace_id,
        query=result["policy"]["sanitized_input"],
        status=result["status"],
        policy_decision=result["policy"]["decision"],
        latency_ms=(perf_counter() - started_at) * 1000,
        sources=result.get("sources", []),
    )
    return result


def retrieve_documents(question: str, *, fetch_live_pages: bool = False) -> dict[str, Any]:
    """Retrieve trusted CouncilQ documents and source metadata."""
    from .rag import search_council_sources

    return search_council_sources(question, fetch_live_pages=fetch_live_pages)


def hybrid_search(
    question: str,
    *,
    vector_db_path: Path = VECTOR_DB_FILE,
    text_directory: Path = TEXT_DIRECTORY,
    dense_limit: int = 20,
    lexical_limit: int = 20,
    limit: int = 5,
    rrf_k: int = 60,
    reranker: Reranker | None = None,
) -> list[dict[str, Any]]:
    """Return document chunks merged from dense and lexical rankings with RRF."""
    query_variants = rewrite_query(question)
    dense_results = _merge_candidates_by_key(
        result
        for query_variant in query_variants
        for result in _dense_candidates(query_variant, vector_db_path=vector_db_path, limit=dense_limit)
    )
    lexical_results = _merge_candidates_by_key(
        result
        for query_variant in query_variants
        for result in _lexical_candidates(
            query_variant,
            vector_db_path=vector_db_path,
            text_directory=text_directory,
            limit=lexical_limit,
        )
    )
    fused = reciprocal_rank_fusion(
        dense_results,
        lexical_results,
        limit=max(limit * 4, limit),
        rrf_k=rrf_k,
    )
    compressed = compress_context(fused, question)
    reranked = (reranker or ScoreReranker()).rerank(question, compressed, limit=limit)
    for result in reranked:
        result["query_variants"] = query_variants
    return reranked


def reciprocal_rank_fusion(
    dense_results: list[dict[str, Any]],
    lexical_results: list[dict[str, Any]],
    *,
    limit: int = 5,
    rrf_k: int = 60,
) -> list[dict[str, Any]]:
    """Merge dense and lexical results using Reciprocal Rank Fusion."""
    fused: dict[str, dict[str, Any]] = {}

    for rank, item in enumerate(dense_results, start=1):
        key = _candidate_key(item)
        record = fused.setdefault(key, {**item, "dense_rank": None, "lexical_rank": None, "rrf_score": 0.0})
        record["dense_rank"] = rank
        record["retrieval_score"] = item.get("score", item.get("retrieval_score", 0.0))
        record["rrf_score"] += 1.0 / (rrf_k + rank)

    for rank, item in enumerate(lexical_results, start=1):
        key = _candidate_key(item)
        record = fused.setdefault(key, {**item, "dense_rank": None, "lexical_rank": None, "rrf_score": 0.0})
        record["lexical_rank"] = rank
        record["lexical_score"] = item.get("lexical_score", item.get("score", 0.0))
        record["rrf_score"] += 1.0 / (rrf_k + rank)

    return sorted(
        fused.values(),
        key=lambda item: (
            -float(item["rrf_score"]),
            item["metadata"].get("title", ""),
            int(item["metadata"].get("page") or 0),
            int(item["metadata"].get("chunk_id") or 0),
        ),
    )[:limit]


def _dense_candidates(question: str, *, vector_db_path: Path, limit: int) -> list[dict[str, Any]]:
    return [
        _normalize_candidate(result)
        for result in search_vector_database(question, path=vector_db_path, limit=limit)
    ]


def _lexical_candidates(
    question: str,
    *,
    vector_db_path: Path,
    text_directory: Path,
    limit: int,
) -> list[dict[str, Any]]:
    terms = _search_terms(question)
    if not terms:
        return []

    candidates = _vector_records_as_candidates(vector_db_path)
    if not candidates:
        candidates = _page_records_as_candidates(text_directory)

    scored: list[dict[str, Any]] = []
    for candidate in candidates:
        haystack = f"{candidate['metadata'].get('title', '')} {candidate['text']}".lower()
        score = sum(1 for term in terms if term in haystack)
        if score:
            scored.append({**candidate, "lexical_score": float(score)})

    return sorted(
        scored,
        key=lambda item: (
            -float(item["lexical_score"]),
            item["metadata"].get("title", ""),
            int(item["metadata"].get("page") or 0),
            int(item["metadata"].get("chunk_id") or 0),
        ),
    )[:limit]


def _vector_records_as_candidates(vector_db_path: Path) -> list[dict[str, Any]]:
    payload = load_vector_database(vector_db_path)
    if not payload:
        return []
    return [
        {
            "text": record["text"],
            "metadata": record["metadata"],
            "retrieval_score": 0.0,
        }
        for record in payload.get("records", [])
    ]


def _page_records_as_candidates(text_directory: Path) -> list[dict[str, Any]]:
    return [
        {
            "text": page["text"],
            "metadata": {
                "title": page["title"],
                "source": page["source"],
                "source_url": page["source_url"],
                "directory_url": page.get("directory_url", ""),
                "page": page["page"],
                "chunk_id": 0,
                "start_index": 0,
                "content_hash": page.get("content_hash", ""),
            },
            "retrieval_score": 0.0,
        }
        for page in load_extracted_pages(text_directory)
    ]


def _normalize_candidate(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "text": result["text"],
        "metadata": result["metadata"],
        "retrieval_score": float(result.get("score", 0.0)),
        "score": float(result.get("score", 0.0)),
    }


def _merge_candidates_by_key(candidates: Any) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        key = _candidate_key(candidate)
        existing = merged.get(key)
        if existing is None:
            merged[key] = candidate
            continue

        existing["retrieval_score"] = max(
            float(existing.get("retrieval_score", existing.get("score", 0.0))),
            float(candidate.get("retrieval_score", candidate.get("score", 0.0))),
        )
        existing["score"] = max(
            float(existing.get("score", 0.0)),
            float(candidate.get("score", 0.0)),
        )
        existing["lexical_score"] = max(
            float(existing.get("lexical_score", 0.0)),
            float(candidate.get("lexical_score", 0.0)),
        )

    return sorted(
        merged.values(),
        key=lambda item: (
            -float(item.get("retrieval_score", item.get("score", 0.0))),
            -float(item.get("lexical_score", 0.0)),
            item["metadata"].get("title", ""),
            int(item["metadata"].get("page") or 0),
            int(item["metadata"].get("chunk_id") or 0),
        ),
    )


def _candidate_key(item: dict[str, Any]) -> str:
    metadata = item["metadata"]
    return "|".join(
        [
            str(metadata.get("source_url", "")),
            str(metadata.get("page", "")),
            str(metadata.get("chunk_id", "")),
            str(metadata.get("start_index", "")),
        ]
    )


def _search_terms(question: str) -> set[str]:
    stopwords = {"about", "adelaide", "city", "council", "does", "from", "have", "into", "what", "when", "where", "which", "with", "your"}
    return {
        token
        for token in re.findall(r"[a-z0-9]{3,}", question.lower())
        if token not in stopwords
    }
