from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .document_ingestion import (
    TEXT_DIRECTORY,
    VECTOR_DB_FILE,
    chunk_document_pages_recursive,
    load_extracted_pages,
)


DEFAULT_EMBEDDING_MODEL = "thenlper/gte-small"
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 100


class Embedder(Protocol):
    model_name: str

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        ...


@dataclass
class SentenceTransformerEmbedder:
    model_name: str = DEFAULT_EMBEDDING_MODEL
    normalize_embeddings: bool = True

    def __post_init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(self.model_name)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = self._model.encode(
            list(texts),
            normalize_embeddings=self.normalize_embeddings,
            show_progress_bar=False,
        )
        return [list(map(float, vector)) for vector in vectors]


def build_vector_database(
    *,
    text_directory: Path = TEXT_DIRECTORY,
    output_path: Path = VECTOR_DB_FILE,
    embedder: Embedder | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> dict[str, Any]:
    pages = load_extracted_pages(text_directory)
    if not pages:
        raise ValueError(f"No extracted document pages found in {text_directory.resolve()}")

    chunks = chunk_document_pages_recursive(
        pages,
        max_chars=chunk_size,
        overlap=chunk_overlap,
    )
    if not chunks:
        raise ValueError("No document chunks were produced from extracted pages.")

    embedder = embedder or SentenceTransformerEmbedder()
    vectors = [_normalize_vector(vector) for vector in embedder.embed([chunk["text"] for chunk in chunks])]

    records = [
        {
            "id": _record_id(chunk),
            "text": chunk["text"],
            "embedding": vector,
            "metadata": {
                "title": chunk["title"],
                "source": chunk["source"],
                "source_url": chunk["source_url"],
                "directory_url": chunk.get("directory_url", ""),
                "page": chunk["page"],
                "chunk_id": chunk["chunk_id"],
                "start_index": chunk.get("start_index", 0),
                "content_hash": chunk.get("content_hash", ""),
            },
        }
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]

    payload = {
        "schema_version": 1,
        "embedding_model": getattr(embedder, "model_name", DEFAULT_EMBEDDING_MODEL),
        "distance": "cosine",
        "normalized_embeddings": True,
        "chunking": {
            "method": "recursive_character",
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        },
        "record_count": len(records),
        "records": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def load_vector_database(path: Path = VECTOR_DB_FILE) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def search_vector_database(
    question: str,
    *,
    path: Path = VECTOR_DB_FILE,
    embedder: Embedder | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    payload = load_vector_database(path)
    if not payload or not payload.get("records"):
        return []

    embedder = embedder or SentenceTransformerEmbedder(str(payload.get("embedding_model") or DEFAULT_EMBEDDING_MODEL))
    query_vector = _normalize_vector(embedder.embed([question])[0])

    scored: list[dict[str, Any]] = []
    for record in payload["records"]:
        score = _cosine_similarity(query_vector, record["embedding"])
        scored.append(
            {
                "score": score,
                "text": record["text"],
                "metadata": record["metadata"],
            }
        )

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:limit]


def _record_id(chunk: dict[str, Any]) -> str:
    key = "|".join(
        [
            str(chunk["source_url"]),
            str(chunk["page"]),
            str(chunk["chunk_id"]),
            str(chunk.get("start_index", 0)),
            chunk["text"],
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _normalize_vector(vector: Sequence[float]) -> list[float]:
    values = [float(value) for value in vector]
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return values
    return [value / norm for value in values]


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(float(left_value) * float(right_value) for left_value, right_value in zip(left, right, strict=False))
