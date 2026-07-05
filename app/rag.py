from __future__ import annotations

from typing import Any


WASTE_SOURCES = [
    {
        "id": "bin_collection",
        "title": "City of Adelaide bin collection day checker",
        "url": "https://www.cityofadelaide.com.au/resident/recycling-waste/bin-collection-day-checker/",
        "keywords": ["bin collected", "collection day", "when is my bin", "bin day"],
        "requires_location": True,
        "message": "Bin collection days depend on the property address.",
    },
    {
        "id": "bin_requests",
        "title": "City of Adelaide bin requests and issues",
        "url": "https://www.cityofadelaide.com.au/resident/recycling-waste/bin-requests-and-issues/",
        "keywords": ["missed bin", "not collected", "damaged bin", "lost bin", "stolen bin"],
        "requires_location": False,
        "message": "For missed, damaged, lost, or stolen bins, use the City of Adelaide bin requests and issues guidance.",
    },
    {
        "id": "hard_waste",
        "title": "City of Adelaide hard waste collection for residents",
        "url": "https://www.cityofadelaide.com.au/resident/recycling-waste/hard-waste-collection-for-residents/",
        "keywords": ["hard waste", "mattress", "furniture", "old couch"],
        "requires_location": False,
        "message": "Hard waste guidance should be confirmed through the City of Adelaide hard waste collection page.",
    },
    {
        "id": "which_bin",
        "title": "City of Adelaide Which Bin guidance",
        "url": "https://www.cityofadelaide.com.au/resident/recycling-waste/which-bin/",
        "keywords": ["which bin", "pizza box", "recycle", "recycling", "batteries", "dispose"],
        "requires_location": False,
        "message": "For item disposal questions, use City of Adelaide recycling guidance and Which Bin SA where linked.",
    },
    {
        "id": "which_bin_sa",
        "title": "Which Bin SA",
        "url": "https://www.whichbin.sa.gov.au/",
        "keywords": ["which bin", "pizza box", "batteries", "dispose", "recycle"],
        "requires_location": False,
        "message": "Which Bin SA can help identify the correct disposal stream for common items.",
    },
]


def search_council_sources(question: str) -> dict[str, Any]:
    """Return trusted CouncilQ source metadata for supported MVP questions."""
    lowered = question.lower()
    matches = [
        source
        for source in WASTE_SOURCES
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

    return {
        "status": "answered" if unique_sources else "unsupported",
        "message": " ".join(messages) if messages else "",
        "sources": unique_sources,
    }


def _looks_like_address(text: str) -> bool:
    return any(token in text for token in [" street", " st", " road", " rd", " avenue", " ave", " terrace", " tce"])

