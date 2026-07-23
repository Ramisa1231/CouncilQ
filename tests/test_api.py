from fastapi.testclient import TestClient

from app.api import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ask_endpoint_returns_structured_response():
    response = client.post(
        "/ask",
        json={
            "question": "When is my bin collected?",
            "council": "City of Adelaide",
            "fetch_live_pages": False,
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "clarification_required"
    assert "address" in body["answer"].lower()
    assert isinstance(body["sources"], list)
    assert body["trace_id"]
    assert "policy" in body
    assert "live_retrieval" in body


def test_ask_endpoint_emits_retrieval_telemetry(monkeypatch):
    events = []
    monkeypatch.setattr(
        "app.retrieval.log_retrieval_event",
        lambda **event: events.append(event),
    )

    response = client.post(
        "/ask",
        json={
            "question": "When is my bin collected?",
            "council": "City of Adelaide",
            "fetch_live_pages": False,
        },
    )

    assert response.status_code == 200
    assert events
    assert events[0]["query"] == "When is my bin collected?"
    assert events[0]["status"] == "clarification_required"
    assert events[0]["trace_id"]
    assert events[0]["policy_decision"] == "allow"
    assert events[0]["latency_ms"] >= 0


def test_ask_endpoint_can_return_document_page_sources(monkeypatch):
    monkeypatch.setattr(
        "app.rag.load_extracted_pages",
        lambda _directory: [
            {
                "text": "The privacy policy explains personal information handling.",
                "title": "Privacy Policy",
                "source": "privacy-policy.pdf",
                "source_url": "https://d31atr86jnqrq2.cloudfront.net/docs/privacy-policy.pdf",
                "directory_url": "https://www.cityofadelaide.com.au/about-council/plans-reporting/strategies-plans-policies/",
                "page": 4,
                "content_hash": "abc",
            }
        ],
    )

    response = client.post(
        "/ask",
        json={
            "question": "What does the privacy policy say about personal information?",
            "council": "City of Adelaide",
            "fetch_live_pages": False,
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "answered"
    assert body["sources"][0]["title"] == "Privacy Policy, page 4"
    assert body["sources"][0]["page"] == "4"
