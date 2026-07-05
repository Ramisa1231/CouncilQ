from app.workflow_nodes import (
    classify_request,
    policy_screen,
    respond_clarification_required,
    retrieve_sources,
)


def test_clarification_response_includes_source_link():
    classified = classify_request("I need help in picking my bins. i live in Adelaide")
    screened = policy_screen(classified.output)
    retrieved = retrieve_sources(screened.output)

    events = list(respond_clarification_required(retrieved.output))
    response_text = events[0].content.parts[0].text

    assert "Please provide the City of Adelaide property address" in response_text
    assert "Sources:" in response_text
    assert "bin-collection-day-checker" in response_text
