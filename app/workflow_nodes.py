from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from google.adk.events.event import Event
from google.genai import types
from pydantic import BaseModel, Field

from .policy import check_request
from .rag import search_council_sources
from .skills import load_skill_registry


class CouncilRequest(BaseModel):
    """Normalized user request passed between CouncilQ workflow nodes."""

    question: str = Field(description="The sanitized or original user question.")
    council: str = Field(default="City of Adelaide")
    intent: str = Field(default="council_question")
    policy: dict[str, Any] = Field(default_factory=dict)
    retrieval: dict[str, Any] = Field(default_factory=dict)


def classify_request(node_input: Any) -> Event:
    """Classify the incoming ADK message before policy or retrieval runs."""
    question = _extract_text(node_input).strip()
    lowered = question.lower()

    if any(term in lowered for term in ["what skills", "available skills", "skill registry"]):
        return Event(output={"question": question}, route="skills")

    request = CouncilRequest(question=question)
    return Event(output=request.model_dump(), route="council_question")


def policy_screen(node_input: dict[str, Any]) -> Event:
    """Apply policy_guard before any retrieval step."""
    request = CouncilRequest.model_validate(node_input)
    decision = check_request(
        text=request.question,
        requested_tool="rag.search",
        role="public_user",
        environment="development",
    )

    request.question = decision["sanitized_input"]
    request.policy = decision

    if decision["decision"] == "block":
        return Event(output=request.model_dump(), route="blocked")

    if decision["decision"] == "requires_human_approval":
        return Event(output=request.model_dump(), route="requires_human_approval")

    return Event(output=request.model_dump(), route="continue")


def retrieve_sources(node_input: dict[str, Any]) -> Event:
    """Retrieve trusted source metadata for the supported CouncilQ skills."""
    request = CouncilRequest.model_validate(node_input)

    if request.council.lower() != "city of adelaide":
        request.retrieval = {
            "status": "clarification_required",
            "message": "CouncilQ is currently scoped to the City of Adelaide. Please confirm the property or service is in the City of Adelaide council area.",
            "sources": [],
        }
        return Event(output=request.model_dump(), route="clarification_required")

    retrieval = search_council_sources(request.question)
    request.retrieval = retrieval
    return Event(output=request.model_dump(), route=retrieval["status"])


def respond_with_skills(node_input: dict[str, Any]) -> Iterator[Event]:
    """Render the skill registry in ADK web."""
    registry = load_skill_registry()["skills"]
    lines = [
        "I have access to these CouncilQ skills for the City of Adelaide:",
        "",
    ]
    for skill_id, skill in registry.items():
        description = skill["description"] or "No description yet."
        lines.append(f"- {skill['name']} ({skill_id}): {description}")
    lines.append("")
    lines.append("How can I help you with City of Adelaide services today?")
    yield from _final_text("\n".join(lines), {"status": "skills", "skills": registry})


def respond_to_request(node_input: dict[str, Any]) -> Iterator[Event]:
    """Render the final CouncilQ answer for deterministic workflow routes."""
    request = CouncilRequest.model_validate(node_input)
    policy_decision = request.policy.get("decision")
    retrieval = request.retrieval
    status = retrieval.get("status", "blocked" if policy_decision == "block" else "unsupported")

    if policy_decision == "block":
        answer = "I cannot help with that request because it violates CouncilQ safety policy."
        yield from _final_text(answer, {"status": "blocked", "policy": request.policy, "sources": []})
        return

    if policy_decision == "requires_human_approval":
        answer = "That action requires human approval before CouncilQ can continue."
        yield from _final_text(answer, {"status": "requires_human_approval", "policy": request.policy, "sources": []})
        return

    if status == "clarification_required":
        answer = retrieval.get("message", "Please provide a little more detail so I can answer safely.")
        yield from _final_text(answer, {"status": status, "policy": request.policy, "sources": retrieval.get("sources", [])})
        return

    if status != "answered" or not retrieval.get("sources"):
        answer = "I could not find a supported CouncilQ skill or trusted source for that question yet."
        yield from _final_text(answer, {"status": "unsupported", "policy": request.policy, "sources": []})
        return

    source_lines = "\n".join(
        f"- {source['title']}: {source['url']}" for source in retrieval["sources"]
    )
    answer = (
        f"{retrieval['message']}\n\n"
        "Use the linked City of Adelaide source to confirm the latest details before acting.\n\n"
        f"Sources:\n{source_lines}"
    )
    yield from _final_text(
        answer,
        {
            "status": "answered",
            "policy": request.policy,
            "answer": answer,
            "sources": retrieval["sources"],
        },
    )


def respond_blocked(node_input: dict[str, Any]) -> Iterator[Event]:
    yield from respond_to_request(node_input)


def respond_requires_human_approval(node_input: dict[str, Any]) -> Iterator[Event]:
    yield from respond_to_request(node_input)


def respond_answered(node_input: dict[str, Any]) -> Iterator[Event]:
    yield from respond_to_request(node_input)


def respond_clarification_required(node_input: dict[str, Any]) -> Iterator[Event]:
    yield from respond_to_request(node_input)


def respond_unsupported(node_input: dict[str, Any]) -> Iterator[Event]:
    yield from respond_to_request(node_input)


def _extract_text(node_input: Any) -> str:
    if isinstance(node_input, str):
        return node_input

    if isinstance(node_input, dict):
        for key in ["text", "question", "message", "content"]:
            value = node_input.get(key)
            if isinstance(value, str):
                return value

    parts = getattr(node_input, "parts", None)
    if parts:
        return " ".join(
            getattr(part, "text", "") for part in parts if getattr(part, "text", "")
        )

    return str(node_input)


def _final_text(text: str, output: dict[str, Any]) -> Iterator[Event]:
    content = types.Content(role="model", parts=[types.Part.from_text(text=text)])
    yield Event(content=content)
    yield Event(output=output)
