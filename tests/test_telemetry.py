import json

from app.telemetry import log_retrieval_event


def test_telemetry_records_trace_policy_latency_and_source_count(tmp_path):
    log_file = tmp_path / "events.jsonl"

    log_retrieval_event(
        trace_id="trace-123",
        query="My email is [[USER_EMAIL]].",
        status="answered",
        policy_decision="sanitize_and_continue",
        latency_ms=12.34567,
        sources=[
            {
                "title": "Which bin",
                "url": "https://www.cityofadelaide.com.au/resident/recycling-waste/which-bin/",
            }
        ],
        log_file=log_file,
    )

    event = json.loads(log_file.read_text(encoding="utf-8"))
    assert event["trace_id"] == "trace-123"
    assert event["query"] == "My email is [[USER_EMAIL]]."
    assert event["policy_decision"] == "sanitize_and_continue"
    assert event["latency_ms"] == 12.346
    assert event["source_count"] == 1
    assert "text" not in event["sources"][0]
