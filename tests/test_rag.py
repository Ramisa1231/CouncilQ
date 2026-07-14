import json

from app.rag import search_council_sources


def test_bin_collection_requires_address():
    result = search_council_sources("When is my bin collected?")

    assert result["status"] == "clarification_required"
    assert result["sources"][0]["url"].endswith("/bin-collection-day-checker/")


def test_plural_bin_collection_requires_address():
    result = search_council_sources("When are my bins collected?")

    assert result["status"] == "clarification_required"
    assert "address" in result["message"].lower()
    assert result["sources"][0]["url"].endswith("/bin-collection-day-checker/")


def test_typo_bin_collection_requires_address():
    result = search_council_sources("When are my ins collected?")

    assert result["status"] == "clarification_required"
    assert "address" in result["message"].lower()
    assert result["sources"][0]["url"].endswith("/bin-collection-day-checker/")


def test_bin_pickup_language_requires_address():
    result = search_council_sources("I need help in picking my bins. i live in Adelaide")

    assert result["status"] == "clarification_required"
    assert "address" in result["message"].lower()
    assert result["sources"][0]["url"].endswith("/bin-collection-day-checker/")


def test_hard_waste_returns_city_source():
    result = search_council_sources("How do I get rid of an old mattress?")

    assert result["status"] == "answered"
    assert any("hard-waste-collection" in source["url"] for source in result["sources"])


def test_outside_council_location_requires_clarification():
    result = search_council_sources("I live in Norwood. When is my green bin collected?")

    assert result["status"] == "clarification_required"
    assert "outside the City of Adelaide" in result["message"]


def test_live_retrieval_graceful_fallback(monkeypatch):
    class FakeResponse:
        status_code = 503
        headers = {"Content-Type": "text/html"}
        text = ""

    monkeypatch.setattr("app.rag.requests.get", lambda *args, **kwargs: FakeResponse())

    result = search_council_sources("How do I get rid of an old mattress?", fetch_live_pages=True)

    assert result["status"] == "answered"
    assert result["live_retrieval"]["attempted"] is True
    assert result["live_retrieval"]["available"] is False


def test_policy_question_uses_local_extracted_documents(monkeypatch, tmp_path):
    payload = {
        "title": "Privacy Policy",
        "source_file": "privacy-policy.pdf",
        "source_url": "https://d31atr86jnqrq2.cloudfront.net/docs/privacy-policy.pdf",
        "directory_url": "https://www.cityofadelaide.com.au/about-council/plans-reporting/strategies-plans-policies/",
        "pages": [
            {
                "page": 4,
                "text": "The privacy policy explains how personal information is collected and used.",
                "content_hash": "abc",
            }
        ],
    }
    (tmp_path / "privacy-policy.json").write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr("app.rag.DOCUMENT_TEXT_DIRECTORY", tmp_path)

    result = search_council_sources("What does the privacy policy say about personal information?")

    assert result["status"] == "answered"
    assert result["sources"][0]["title"] == "Privacy Policy, page 4"
    assert result["sources"][0]["url"].startswith("https://d31atr86jnqrq2.cloudfront.net/")
    assert result["sources"][0]["page"] == "4"


def test_unmatched_document_question_remains_unsupported(monkeypatch, tmp_path):
    payload = {
        "title": "Privacy Policy",
        "source_file": "privacy-policy.pdf",
        "source_url": "https://d31atr86jnqrq2.cloudfront.net/docs/privacy-policy.pdf",
        "pages": [{"page": 1, "text": "Privacy collection notice."}],
    }
    (tmp_path / "privacy-policy.json").write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr("app.rag.DOCUMENT_TEXT_DIRECTORY", tmp_path)

    result = search_council_sources("How do I register my dog?")

    assert result["status"] == "unsupported"
    assert result["sources"] == []
