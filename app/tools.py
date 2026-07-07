from __future__ import annotations

from typing import Any

from .policy import check_request
from .rag import mentions_outside_city_of_adelaide, search_council_sources
from .skills import load_skill_registry


def inspect_skill_registry() -> dict[str, Any]:
    """List available CouncilQ skills and their routing descriptions."""
    return load_skill_registry()


def answer_council_question(
    question: str,
    council: str = "City of Adelaide",
    *,
    fetch_live_pages: bool = True,
) -> dict[str, Any]:
    """Answer a City of Adelaide council question using the CouncilQ skill registry and trusted sources."""
    policy_decision = check_request(
        text=question,
        requested_tool="rag.search",
        role="public_user",
        environment="development",
    )

    if policy_decision["decision"] == "block":
        return {
            "status": "blocked",
            "policy": policy_decision,
            "answer": "I cannot help with that request because it violates CouncilQ safety policy.",
            "sources": [],
            "live_retrieval": {"attempted": False, "available": False, "note": "Live retrieval not attempted.", "pages": []},
        }

    safe_question = policy_decision["sanitized_input"]
    if council.lower() != "city of adelaide" or mentions_outside_city_of_adelaide(safe_question.lower()):
        return {
            "status": "clarification_required",
            "policy": policy_decision,
            "answer": "CouncilQ is currently scoped to the City of Adelaide. Please confirm the property or service is in the City of Adelaide council area before I continue.",
            "sources": [],
            "live_retrieval": {"attempted": False, "available": False, "note": "Live retrieval not attempted.", "pages": []},
        }

    retrieval = search_council_sources(safe_question, fetch_live_pages=fetch_live_pages)
    if retrieval["status"] == "clarification_required":
        return {
            "status": "clarification_required",
            "policy": policy_decision,
            "answer": retrieval["message"],
            "sources": retrieval["sources"],
            "live_retrieval": retrieval.get("live_retrieval", {"attempted": False, "available": False, "note": "Live retrieval not attempted.", "pages": []}),
        }

    if not retrieval["sources"]:
        return {
            "status": "unsupported",
            "policy": policy_decision,
            "answer": "I could not find a supported CouncilQ skill or trusted source for that question yet.",
            "sources": [],
            "live_retrieval": retrieval.get("live_retrieval", {"attempted": False, "available": False, "note": "Live retrieval not attempted.", "pages": []}),
        }

    source_lines = "\n".join(f"- {source['title']}: {source['url']}" for source in retrieval["sources"])
    answer = (
        f"{retrieval['message']}\n\n"
        "Use the linked City of Adelaide source to confirm the latest details before acting.\n\n"
        f"Sources:\n{source_lines}"
    )
    return {
        "status": "answered",
        "policy": policy_decision,
        "answer": answer,
        "sources": retrieval["sources"],
        "live_retrieval": retrieval.get("live_retrieval", {"attempted": False, "available": False, "note": "Live retrieval not attempted.", "pages": []}),
    }
