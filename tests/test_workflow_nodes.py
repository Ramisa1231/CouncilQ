import base64
import json

from app.workflow_nodes import (
    classify_request,
    normalize_event,
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


def test_normalize_event_accepts_plain_json_data():
    payload = {
        "data": {
            "question": "Where can I recycle batteries?",
            "council": "City of Adelaide",
        }
    }

    event = normalize_event(json.dumps(payload))

    assert event.output["question"] == "Where can I recycle batteries?"
    assert event.output["metadata"]["input_mode"] == "json_event"
    assert event.actions.route == "normalized"
    assert event.actions.state_delta["councilq_stage"] == "normalized"


def test_normalize_event_accepts_base64_pubsub_data():
    data = json.dumps({"message": "I need help in picking my bins. i live in Adelaide"})
    payload = {"data": base64.b64encode(data.encode("utf-8")).decode("ascii")}

    normalized = normalize_event(json.dumps(payload))
    classified = classify_request(normalized.output)
    screened = policy_screen(classified.output)
    retrieved = retrieve_sources(screened.output)

    assert normalized.output["question"] == "I need help in picking my bins. i live in Adelaide"
    assert classified.actions.route == "council_question"
    assert retrieved.actions.route == "clarification_required"
