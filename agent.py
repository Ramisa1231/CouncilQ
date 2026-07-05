from google.adk.workflow import Workflow

from .app.workflow_nodes import (
    classify_request,
    policy_screen,
    respond_answered,
    respond_blocked,
    respond_clarification_required,
    respond_requires_human_approval,
    respond_unsupported,
    respond_with_skills,
    retrieve_sources,
)


COUNCILQ_DESCRIPTION = "Single-agent RAG workflow assistant for City of Adelaide services."


root_agent = Workflow(
    name="councilq",
    description=COUNCILQ_DESCRIPTION,
    edges=[
        ("START", classify_request),
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
                "requires_human_approval": respond_requires_human_approval,
                "continue": retrieve_sources,
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
