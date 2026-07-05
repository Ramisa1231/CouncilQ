from app.rag import search_council_sources


def test_bin_collection_requires_address():
    result = search_council_sources("When is my bin collected?")

    assert result["status"] == "clarification_required"
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

