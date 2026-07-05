from google.adk.workflow import Workflow

from .app.workflow_nodes import (
    classify_request,
    policy_screen,
    respond_to_request,
    respond_with_skills,
    retrieve_sources,
)


COUNCILQ_DESCRIPTION = "Single-agent RAG workflow assistant for City of Adelaide services."


root_agent = Workflow(
    name="councilq",
    description=COUNCILQ_DESCRIPTION,
    edges=[
        ("START", classify_request),
        (classify_request, respond_with_skills, "skills"),
        (classify_request, policy_screen, "council_question"),
        (policy_screen, respond_to_request, "blocked"),
        (policy_screen, respond_to_request, "requires_human_approval"),
        (policy_screen, retrieve_sources, "continue"),
        (retrieve_sources, respond_to_request, "answered"),
        (retrieve_sources, respond_to_request, "clarification_required"),
        (retrieve_sources, respond_to_request, "unsupported"),
    ],
)

__all__ = ["root_agent"]
