from __future__ import annotations

import base64
import binascii
from collections.abc import Iterator
import json
from typing import Any

from google.adk.agents.context import Context
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.workflow import node
from google.genai import types
from pydantic import BaseModel, Field

try:
    from ..config import HUMAN_REVIEW_INTERRUPT_ID
except ImportError:
    from config import HUMAN_REVIEW_INTERRUPT_ID
from .policy import check_request
from .rag import mentions_outside_city_of_adelaide, search_council_sources
from .skills import load_skill_registry


class CouncilRequest(BaseModel):
    """Normalized user request passed between CouncilQ workflow nodes."""

    question: str = Field(description="The sanitized or original user question.")
    council: str = Field(default="City of Adelaide")
    intent: str = Field(default="council_question")
    policy: dict[str, Any] = Field(default_factory=dict)
    retrieval: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HumanReviewDecision(BaseModel):
    """Human approval decision captured through ADK RequestInput."""

    decision: str = Field(description="approve or reject")
    reason: str = Field(default="")


def normalize_event(node_input: Any) -> Event:
    """Normalize chat text or Pub/Sub-style JSON into a CouncilQ request."""
    text = _extract_text(node_input).strip()
    payload = _parse_json(text)
    event_data = _extract_event_data(payload) if isinstance(payload, dict) else {}

    if event_data:
        question = _first_text(event_data, ["question", "message", "text", "query", "description"])
        council = _first_text(event_data, ["council", "council_area"]) or "City of Adelaide"
        request = CouncilRequest(
            question=question or text,
            council=council,
            metadata={
                "input_mode": "json_event",
                "event_keys": sorted(event_data.keys()),
                "fetch_live_pages": bool(event_data.get("fetch_live_pages", False)),
            },
        )
    else:
        request = CouncilRequest(
            question=text,
            metadata={"input_mode": "chat_text", "fetch_live_pages": False},
        )

    return Event(
        output=request.model_dump(),
        route="normalized",
        state=_state_update("normalized", request),
    )


def classify_request(node_input: Any) -> Event:
    """Classify the incoming ADK message before policy or retrieval runs."""
    request = _request_from_input(node_input)
    question = request.question.strip()
    lowered = question.lower()

    if any(term in lowered for term in ["what skills", "available skills", "skill registry"]):
        return Event(
            output=request.model_dump(),
            route="skills",
            state=_state_update("classified_skills", request),
        )

    request.intent = "council_question"
    return Event(
        output=request.model_dump(),
        route="council_question",
        state=_state_update("classified_council_question", request),
    )


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
        return Event(
            output=request.model_dump(),
            route="blocked",
            state=_state_update("policy_blocked", request),
        )

    if decision["decision"] == "requires_human_approval":
        return Event(
            output=request.model_dump(),
            route="requires_human_approval",
            state=_state_update("policy_requires_human_approval", request),
        )

    return Event(
        output=request.model_dump(),
        route="continue",
        state=_state_update("policy_passed", request),
    )


def retrieve_sources(node_input: dict[str, Any]) -> Event:
    """Retrieve trusted source metadata for the supported CouncilQ skills."""
    request = CouncilRequest.model_validate(node_input)

    if request.council.lower() != "city of adelaide" or mentions_outside_city_of_adelaide(request.question.lower()):
        request.retrieval = {
            "status": "clarification_required",
            "message": "CouncilQ is currently scoped to the City of Adelaide. Please confirm the property or service is in the City of Adelaide council area before I continue.",
            "sources": [],
        }
        return Event(
            output=request.model_dump(),
            route="clarification_required",
            state=_state_update("retrieval_clarification_required", request),
        )

    retrieval = search_council_sources(
        request.question,
        fetch_live_pages=bool(request.metadata.get("fetch_live_pages", False)),
    )
    request.retrieval = retrieval
    return Event(
        output=request.model_dump(),
        route=retrieval["status"],
        state=_state_update(f"retrieval_{retrieval['status']}", request),
    )


@node(rerun_on_resume=True)
def request_human_approval(ctx: Context, node_input: dict[str, Any]) -> Iterator[Event | RequestInput]:
    """Pause the workflow for a human decision on high-risk requests."""
    request = CouncilRequest.model_validate(node_input)
    resume_value = _resume_input(ctx)

    if resume_value is None:
        message = (
            "CouncilQ needs human approval before continuing with this request.\n\n"
            f"Question: {request.question}\n"
            f"Policy reason: {request.policy.get('reason', 'requires_human_approval')}\n\n"
            "Respond with approve or reject, and include a reason if helpful."
        )
        yield RequestInput(
            interrupt_id=HUMAN_REVIEW_INTERRUPT_ID,
            message=message,
            payload=request.model_dump(),
            response_schema=HumanReviewDecision,
        )
        return

    decision = _human_decision(resume_value)
    request.metadata["human_review"] = decision
    route = "human_approved" if decision["decision"] == "approve" else "human_rejected"
    yield Event(
        output=request.model_dump(),
        route=route,
        state=_state_update(route, request, {"human_review": decision}),
    )


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
        human_review = request.metadata.get("human_review", {})
        if human_review:
            answer = (
                f"Human review recorded: {human_review['decision']}.\n\n"
                f"Reason: {human_review.get('reason') or 'No reason provided.'}"
            )
        else:
            answer = "That action requires human approval before CouncilQ can continue."
        yield from _final_text(answer, {"status": "requires_human_approval", "policy": request.policy, "sources": []})
        return

    if status == "clarification_required":
        answer = retrieval.get("message", "Please provide a little more detail so I can answer safely.")
        source_lines = _format_sources(retrieval.get("sources", []))
        if source_lines:
            answer = f"{answer}\n\nSources:\n{source_lines}"
        yield from _final_text(answer, {"status": status, "policy": request.policy, "sources": retrieval.get("sources", [])})
        return

    if status != "answered" or not retrieval.get("sources"):
        answer = "I could not find a supported CouncilQ skill or trusted source for that question yet."
        yield from _final_text(answer, {"status": "unsupported", "policy": request.policy, "sources": []})
        return

    source_lines = _format_sources(retrieval["sources"])
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


def respond_human_approved(node_input: dict[str, Any]) -> Iterator[Event]:
    yield from respond_to_request(node_input)


def respond_human_rejected(node_input: dict[str, Any]) -> Iterator[Event]:
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


def _request_from_input(node_input: Any) -> CouncilRequest:
    if isinstance(node_input, dict) and "question" in node_input:
        return CouncilRequest.model_validate(node_input)
    return CouncilRequest(question=_extract_text(node_input).strip())


def _parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _extract_event_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", payload)
    if isinstance(data, dict):
        return data

    if not isinstance(data, str):
        return {}

    plain_json = _parse_json(data)
    if isinstance(plain_json, dict):
        return plain_json

    try:
        decoded = base64.b64decode(data, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return {}

    decoded_json = _parse_json(decoded)
    return decoded_json if isinstance(decoded_json, dict) else {}


def _first_text(payload: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _resume_input(ctx: Context) -> Any:
    resume_inputs = getattr(ctx, "resume_inputs", {}) or {}
    if HUMAN_REVIEW_INTERRUPT_ID in resume_inputs:
        return resume_inputs[HUMAN_REVIEW_INTERRUPT_ID]
    if resume_inputs:
        return next(iter(resume_inputs.values()))
    return None


def _human_decision(value: Any) -> dict[str, str]:
    if isinstance(value, HumanReviewDecision):
        decision = value.decision
        reason = value.reason
    elif isinstance(value, dict):
        decision = str(value.get("decision", value.get("action", "")))
        reason = str(value.get("reason", ""))
    else:
        decision = str(value)
        reason = ""

    normalized = decision.strip().lower()
    if normalized in {"approved", "yes", "y"}:
        normalized = "approve"
    if normalized not in {"approve", "reject"}:
        normalized = "reject"

    return {"decision": normalized, "reason": reason.strip()}


def _state_update(stage: str, request: CouncilRequest, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    state = {
        "councilq_stage": stage,
        "councilq_request": request.model_dump(),
    }
    if extra:
        state.update(extra)
    return state


def _format_sources(sources: list[dict[str, str]]) -> str:
    return "\n".join(f"- {source['title']}: {source['url']}" for source in sources)


def _final_text(text: str, output: dict[str, Any]) -> Iterator[Event]:
    content = types.Content(role="model", parts=[types.Part.from_text(text=text)])
    yield Event(content=content)
    yield Event(output=output)
