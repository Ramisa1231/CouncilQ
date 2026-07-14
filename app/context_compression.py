from __future__ import annotations

import re


def compress_context(chunks: list[dict], query: str, *, max_chars: int = 1200) -> list[dict]:
    """Select relevant extractive snippets from retrieved chunks."""
    terms = {term for term in re.findall(r"[a-z0-9]{3,}", query.lower())}
    compressed: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        key = (metadata.get("source_url", ""), str(metadata.get("page", "")))
        if key in seen:
            continue
        seen.add(key)

        sentences = re.split(r"(?<=[.!?])\s+", chunk.get("text", ""))
        selected = [sentence for sentence in sentences if terms & set(re.findall(r"[a-z0-9]{3,}", sentence.lower()))]
        text = " ".join(selected or sentences)[:max_chars].strip()
        if text:
            compressed.append({**chunk, "text": text})

    return compressed
