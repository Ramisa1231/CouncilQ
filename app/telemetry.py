from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL_LOG_FILE = ROOT / "data" / "indexes" / "retrieval_logs.jsonl"


def log_retrieval_event(
    *,
    trace_id: str,
    query: str,
    status: str,
    policy_decision: str,
    latency_ms: float,
    sources: list[dict[str, Any]],
    log_file: Path = RETRIEVAL_LOG_FILE,
) -> None:
    """Append one sanitized pipeline event for offline debugging."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "query": query,
        "status": status,
        "policy_decision": policy_decision,
        "latency_ms": round(latency_ms, 3),
        "source_count": len(sources),
        "sources": [
            {
                "title": source.get("title", ""),
                "url": source.get("url", ""),
                "page": source.get("page", ""),
                "chunk_id": source.get("chunk_id", ""),
                "rrf_score": source.get("rrf_score", ""),
                "retrieval_score": source.get("retrieval_score", ""),
                "lexical_score": source.get("lexical_score", ""),
                "rerank_score": source.get("rerank_score", ""),
                "dense_rank": source.get("dense_rank", ""),
                "lexical_rank": source.get("lexical_rank", ""),
                "rerank_rank": source.get("rerank_rank", ""),
            }
            for source in sources
        ],
    }
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
