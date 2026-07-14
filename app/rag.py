from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

import requests

from .document_ingestion import load_extracted_pages
from .vector_db import search_vector_database


ROOT = Path(__file__).resolve().parents[1]
WASTE_SOURCES_PATH = ROOT / "skills" / "waste_and_recycling" / "assets" / "sources.json"
DOCUMENT_TEXT_DIRECTORY = ROOT / "data" / "extracted" / "json"
ALLOWED_SOURCE_DOMAINS = {
    "cityofadelaide.com.au",
    "www.cityofadelaide.com.au",
    "whichbin.sa.gov.au",
    "www.whichbin.sa.gov.au",
}
KNOWN_OUTSIDE_CITY_OF_ADELAIDE = {"norwood"}


def search_council_sources(
    question: str,
    *,
    fetch_live_pages: bool = False,
    timeout_seconds: float = 2.0,
) -> dict[str, Any]:
    """Return trusted CouncilQ source metadata for supported MVP questions."""
    lowered = question.lower()

    if mentions_outside_city_of_adelaide(lowered):
        return {
            "status": "clarification_required",
            "message": "That location may be outside the City of Adelaide service area. Please confirm your council before I provide collection guidance.",
            "sources": [],
            "live_retrieval": _empty_live_retrieval(attempted=False),
        }

    matches = _matching_waste_sources(lowered)

    if any(source["requires_location"] for source in matches) and not _looks_like_address(lowered):
        return {
            "status": "clarification_required",
            "message": "Please provide the City of Adelaide property address or use the official bin collection day checker. I should not guess a collection day.",
            "sources": [
                {
                    "title": "City of Adelaide bin collection day checker",
                    "url": "https://www.cityofadelaide.com.au/resident/recycling-waste/bin-collection-day-checker/",
                }
            ],
            "live_retrieval": _empty_live_retrieval(attempted=False),
        }

    unique_sources: list[dict[str, str]] = []
    seen: set[str] = set()
    messages: list[str] = []
    for source in matches:
        if source["url"] not in seen:
            unique_sources.append({"title": source["title"], "url": source["url"]})
            seen.add(source["url"])
        if source["message"] not in messages:
            messages.append(source["message"])

    result = {
        "status": "answered" if unique_sources else "unsupported",
        "message": " ".join(messages) if messages else "",
        "sources": unique_sources,
        "live_retrieval": _empty_live_retrieval(attempted=False),
    }

    if not unique_sources:
        document_result = search_extracted_documents(question)
        if document_result["sources"]:
            return document_result

    if fetch_live_pages and unique_sources:
        result["live_retrieval"] = fetch_live_source_summaries(unique_sources, timeout_seconds=timeout_seconds)

    return result


def search_extracted_documents(
    question: str,
    *,
    directory: Path | None = None,
    limit: int = 3,
) -> dict[str, Any]:
    """Search locally indexed City of Adelaide documents, preferring vector_db.json when present."""
    directory = directory or DOCUMENT_TEXT_DIRECTORY
    vector_matches = search_vector_database(question, limit=limit)
    if vector_matches:
        return _document_result_from_vector_matches(vector_matches)

    pages = load_extracted_pages(directory)
    if not pages:
        return {
            "status": "unsupported",
            "message": "",
            "sources": [],
            "live_retrieval": _empty_live_retrieval(attempted=False),
        }

    query_terms = _search_terms(question)
    scored: list[tuple[int, dict[str, Any]]] = []
    for page in pages:
        haystack = f"{page['title']} {page['text']}".lower()
        score = sum(1 for term in query_terms if term in haystack)
        if score:
            scored.append((score, page))

    scored.sort(key=lambda item: (-item[0], item[1]["title"], int(item[1].get("page") or 0)))
    matches = [page for _, page in scored[:limit]]
    if not matches:
        return {
            "status": "unsupported",
            "message": "",
            "sources": [],
            "live_retrieval": _empty_live_retrieval(attempted=False),
        }

    sources = [
        {
            "title": f"{page['title']}, page {page['page']}",
            "url": page["source_url"],
            "page": str(page["page"]),
            "source_file": page["source"],
        }
        for page in matches
    ]
    return {
        "status": "answered",
        "message": "I found relevant City of Adelaide document pages in the local CouncilQ document index.",
        "sources": sources,
        "live_retrieval": _empty_live_retrieval(attempted=False),
    }


def _document_result_from_vector_matches(matches: list[dict[str, Any]]) -> dict[str, Any]:
    sources = []
    for match in matches:
        metadata = match["metadata"]
        sources.append(
            {
                "title": f"{metadata['title']}, page {metadata['page']}",
                "url": metadata["source_url"],
                "page": str(metadata["page"]),
                "source_file": metadata["source"],
                "score": f"{match['score']:.6f}",
            }
        )

    return {
        "status": "answered",
        "message": "I found relevant City of Adelaide document chunks in the local CouncilQ vector index.",
        "sources": sources,
        "live_retrieval": _empty_live_retrieval(attempted=False),
    }


def fetch_live_source_summaries(
    sources: list[dict[str, str]],
    *,
    timeout_seconds: float = 2.0,
) -> dict[str, Any]:
    """Fetch brief snippets from trusted source pages, with graceful fallback."""
    pages: list[dict[str, str]] = []
    for source in sources:
        page = _fetch_trusted_page_summary(source["url"], timeout_seconds=timeout_seconds)
        if not page:
            continue
        pages.append(
            {
                "title": source["title"],
                "url": source["url"],
                "snippet": page["snippet"],
            }
        )

    if pages:
        return {
            "attempted": True,
            "available": True,
            "note": "Live retrieval succeeded for one or more trusted pages.",
            "pages": pages,
        }

    return {
        "attempted": True,
        "available": False,
        "note": "Live retrieval is unavailable right now. Using curated trusted source links.",
        "pages": [],
    }


def _fetch_trusted_page_summary(url: str, *, timeout_seconds: float) -> dict[str, str] | None:
    host = (urlparse(url).hostname or "").lower()
    if host not in ALLOWED_SOURCE_DOMAINS:
        return None

    try:
        response = requests.get(
            url,
            timeout=timeout_seconds,
            headers={"User-Agent": "CouncilQ/0.1"},
        )
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    content_type = (response.headers.get("Content-Type") or "").lower()
    if "html" not in content_type:
        return None

    snippet = _html_to_snippet(response.text)
    if not snippet:
        return None

    return {"snippet": snippet}


def _html_to_snippet(html: str, *, max_chars: int = 280) -> str:
    without_scripts = re.sub(r"<script[\\s\\S]*?</script>", " ", html, flags=re.IGNORECASE)
    without_styles = re.sub(r"<style[\\s\\S]*?</style>", " ", without_scripts, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", without_styles)
    collapsed = re.sub(r"\\s+", " ", text).strip()
    return collapsed[:max_chars].rstrip()


def _search_terms(question: str) -> set[str]:
    stopwords = {
        "about",
        "adelaide",
        "city",
        "council",
        "does",
        "from",
        "have",
        "into",
        "what",
        "when",
        "where",
        "which",
        "with",
        "your",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]{3,}", question.lower())
        if token not in stopwords
    }


def _matching_waste_sources(lowered_question: str) -> list[dict[str, Any]]:
    sources = _load_waste_sources()
    matches = [
        source
        for source in sources
        if any(keyword in lowered_question for keyword in source["keywords"])
    ]

    if _looks_like_bin_collection_question(lowered_question):
        bin_collection = next(
            source for source in sources if source["id"] == "bin_collection"
        )
        if bin_collection not in matches:
            matches.append(bin_collection)

    return matches


def _looks_like_bin_collection_question(text: str) -> bool:
    if re.search(r"\b(missed|not collected|damaged|lost|stolen)\b", text):
        return False

    if not re.search(r"\b(when|what day|which day|collection day|collected|pickup|pick up)\b", text):
        return False

    return bool(
        re.search(r"\bbins?\b", text)
        or re.search(r"\bmy\s+ins\b", text)
        or re.search(r"\bins\s+collected\b", text)
    )


@lru_cache(maxsize=1)
def _load_waste_sources() -> list[dict[str, Any]]:
    import json

    payload = json.loads(WASTE_SOURCES_PATH.read_text(encoding="utf-8"))
    return payload["sources"]


def mentions_outside_city_of_adelaide(text: str) -> bool:
    return any(suburb in text for suburb in KNOWN_OUTSIDE_CITY_OF_ADELAIDE)


def _looks_like_address(text: str) -> bool:
    return any(token in text for token in [" street", " st", " road", " rd", " avenue", " ave", " terrace", " tce"])


def _empty_live_retrieval(*, attempted: bool) -> dict[str, Any]:
    return {
        "attempted": attempted,
        "available": False,
        "note": "Live retrieval not attempted.",
        "pages": [],
    }
