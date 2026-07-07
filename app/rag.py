from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

import requests


ROOT = Path(__file__).resolve().parents[1]
WASTE_SOURCES_PATH = ROOT / "skills" / "waste_and_recycling" / "assets" / "sources.json"
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

    matches = [
        source
        for source in _load_waste_sources()
        if any(keyword in lowered for keyword in source["keywords"])
    ]

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

    if fetch_live_pages and unique_sources:
        result["live_retrieval"] = fetch_live_source_summaries(unique_sources, timeout_seconds=timeout_seconds)

    return result


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
