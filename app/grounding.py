from __future__ import annotations

from urllib.parse import urlparse


TRUSTED_SOURCE_DOMAINS = {
    "cityofadelaide.com.au",
    "www.cityofadelaide.com.au",
    "whichbin.sa.gov.au",
    "www.whichbin.sa.gov.au",
    "d31atr86jnqrq2.cloudfront.net",
}


def validate_retrieval_grounding(retrieval: dict) -> dict:
    """Validate that answered retrievals carry trusted citations."""
    if retrieval.get("status") != "answered":
        return retrieval

    sources = retrieval.get("sources", [])
    if not sources:
        return _unsupported("No citations were returned for the answer.")

    for source in sources:
        url = str(source.get("url", ""))
        if not _is_trusted_url(url):
            return _unsupported(f"Untrusted citation URL: {url}")
        if url.lower().endswith(".pdf") and not source.get("page"):
            return _unsupported(f"PDF citation is missing a page number: {url}")

    return retrieval


def _unsupported(message: str) -> dict:
    return {
        "status": "unsupported",
        "message": message,
        "sources": [],
        "live_retrieval": {
            "attempted": False,
            "available": False,
            "note": "Live retrieval not attempted.",
            "pages": [],
        },
    }


def _is_trusted_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in TRUSTED_SOURCE_DOMAINS
