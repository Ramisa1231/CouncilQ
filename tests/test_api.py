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
    assert "policy" in body
    assert "live_retrieval" in body
