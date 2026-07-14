from __future__ import annotations

from typing import Any

from .answer import format_answer
from .grounding import validate_retrieval_grounding
from .policy import check_request
from .rag import mentions_outside_city_of_adelaide, search_council_sources


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
            "live_retrieval": EMPTY_LIVE_RETRIEVAL,
        }

    safe_question = policy_decision["sanitized_input"]
    if council.lower() != "city of adelaide" or mentions_outside_city_of_adelaide(safe_question.lower()):
        return {
            "status": "clarification_required",
            "policy": policy_decision,
            "answer": "CouncilQ is currently scoped to the City of Adelaide. Please confirm the property or service is in the City of Adelaide council area before I continue.",
            "sources": [],
            "live_retrieval": EMPTY_LIVE_RETRIEVAL,
        }

    retrieval = validate_retrieval_grounding(
        retrieve_documents(safe_question, fetch_live_pages=fetch_live_pages)
    )
    if retrieval["status"] == "clarification_required":
        return {
            "status": "clarification_required",
            "policy": policy_decision,
            "answer": retrieval["message"],
            "sources": retrieval["sources"],
            "live_retrieval": retrieval.get("live_retrieval", EMPTY_LIVE_RETRIEVAL),
        }

    if not retrieval["sources"]:
        return {
            "status": "unsupported",
            "policy": policy_decision,
            "answer": "I could not find trusted City of Adelaide source material for that question yet.",
            "sources": [],
            "live_retrieval": retrieval.get("live_retrieval", EMPTY_LIVE_RETRIEVAL),
        }

    answer = format_answer(retrieval["message"], retrieval["sources"])
    return {
        "status": "answered",
        "policy": policy_decision,
        "answer": answer,
        "sources": retrieval["sources"],
        "live_retrieval": retrieval.get("live_retrieval", EMPTY_LIVE_RETRIEVAL),
    }


def retrieve_documents(question: str, *, fetch_live_pages: bool = False) -> dict[str, Any]:
    """Retrieve trusted CouncilQ documents and source metadata."""
    return search_council_sources(question, fetch_live_pages=fetch_live_pages)
