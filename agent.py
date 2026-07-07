from google.adk.workflow import Workflow

from .app.workflow_nodes import (
    classify_request,
    normalize_event,
    policy_screen,
    respond_answered,
    respond_blocked,
    respond_clarification_required,
    respond_human_approved,
    respond_human_rejected,
    respond_unsupported,
    respond_with_skills,
    request_human_approval,
    retrieve_sources,
)


COUNCILQ_DESCRIPTION = "Single-agent RAG workflow assistant for City of Adelaide services."


root_agent = Workflow(
    name="councilq",
    description=COUNCILQ_DESCRIPTION,
    edges=[
        ("START", normalize_event),
        (normalize_event, {"normalized": classify_request}),
        (
            classify_request,
            {
                "skills": respond_with_skills,
                "council_question": policy_screen,
            },
        ),
        (
            policy_screen,
            {
                "blocked": respond_blocked,
                "requires_human_approval": request_human_approval,
                "continue": retrieve_sources,
            },
        ),
        (
            request_human_approval,
            {
                "human_approved": respond_human_approved,
                "human_rejected": respond_human_rejected,
            },
        ),
        (
            retrieve_sources,
            {
                "answered": respond_answered,
                "clarification_required": respond_clarification_required,
                "unsupported": respond_unsupported,
            },
        ),
    ],
)

__all__ = ["root_agent"]
