import json

from app.retrieval import hybrid_search, reciprocal_rank_fusion


def _record(record_id, title, text, embedding, *, page=1, chunk_id=0):
    return {
        "id": record_id,
        "text": text,
        "embedding": embedding,
        "metadata": {
            "title": title,
            "source": f"{record_id}.pdf",
            "source_url": f"https://d31atr86jnqrq2.cloudfront.net/docs/{record_id}.pdf",
            "directory_url": "",
            "page": page,
            "chunk_id": chunk_id,
            "start_index": 0,
            "content_hash": record_id,
        },
    }


def test_rrf_merges_dense_and_lexical_rankings():
    dense = [
        {"text": "A", "metadata": {"source_url": "u1", "page": 1, "chunk_id": 0, "title": "A"}, "score": 0.9},
        {"text": "B", "metadata": {"source_url": "u2", "page": 1, "chunk_id": 0, "title": "B"}, "score": 0.8},
    ]
    lexical = [
        {"text": "B", "metadata": {"source_url": "u2", "page": 1, "chunk_id": 0, "title": "B"}, "lexical_score": 2.0},
        {"text": "C", "metadata": {"source_url": "u3", "page": 1, "chunk_id": 0, "title": "C"}, "lexical_score": 1.0},
    ]

    results = reciprocal_rank_fusion(dense, lexical, limit=3, rrf_k=60)

    assert [result["metadata"]["source_url"] for result in results] == ["u2", "u1", "u3"]
    assert results[0]["dense_rank"] == 2
    assert results[0]["lexical_rank"] == 1
    assert results[0]["rrf_score"] > results[1]["rrf_score"]


def test_hybrid_search_returns_dense_only_when_lexical_has_no_match(monkeypatch, tmp_path):
    vector_path = tmp_path / "vector_db.json"
    vector_path.write_text(
        json.dumps(
            {
                "embedding_model": "test",
                "records": [
                    _record("privacy", "Privacy Policy", "Personal information handling.", [1.0, 0.0]),
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.retrieval.search_vector_database",
        lambda question, path, limit: [
            {
                "score": 0.9,
                "text": "Personal information handling.",
                "metadata": {
                    "title": "Privacy Policy",
                    "source": "privacy.pdf",
                    "source_url": "https://d31atr86jnqrq2.cloudfront.net/docs/privacy.pdf",
                    "page": 4,
                    "chunk_id": 0,
                    "start_index": 0,
                },
            }
        ],
    )

    results = hybrid_search("unmatched dense query", vector_db_path=vector_path, text_directory=tmp_path, limit=1)

    assert len(results) == 1
    assert results[0]["dense_rank"] == 1
    assert results[0]["lexical_rank"] is None


def test_hybrid_search_returns_lexical_only_without_vector_db(tmp_path):
    text_dir = tmp_path / "text"
    text_dir.mkdir()
    payload = {
        "title": "Privacy Policy",
        "source_file": "privacy-policy.pdf",
        "source_url": "https://d31atr86jnqrq2.cloudfront.net/docs/privacy-policy.pdf",
        "directory_url": "",
        "pages": [{"page": 4, "text": "Privacy policy explains personal information handling."}],
    }
    (text_dir / "privacy-policy.json").write_text(json.dumps(payload), encoding="utf-8")

    results = hybrid_search("personal information", vector_db_path=tmp_path / "missing.json", text_directory=text_dir, limit=1)

    assert len(results) == 1
    assert results[0]["dense_rank"] is None
    assert results[0]["lexical_rank"] == 1
    assert results[0]["metadata"]["title"] == "Privacy Policy"


def test_hybrid_search_combines_dense_and_lexical_for_same_chunk(monkeypatch, tmp_path):
    vector_path = tmp_path / "vector_db.json"
    record = _record("privacy", "Privacy Policy", "Privacy policy personal information handling.", [1.0, 0.0], page=4)
    vector_path.write_text(json.dumps({"embedding_model": "test", "records": [record]}), encoding="utf-8")
    monkeypatch.setattr(
        "app.retrieval.search_vector_database",
        lambda question, path, limit: [
            {"score": 0.9, "text": record["text"], "metadata": record["metadata"]}
        ],
    )

    results = hybrid_search("privacy personal information", vector_db_path=vector_path, text_directory=tmp_path, limit=1)

    assert len(results) == 1
    assert results[0]["dense_rank"] == 1
    assert results[0]["lexical_rank"] == 1
    assert results[0]["rrf_score"] > 0.03
    assert results[0]["rerank_rank"] == 1


def test_hybrid_search_uses_query_expansion_for_lexical_matches(tmp_path):
    vector_path = tmp_path / "missing.json"
    text_dir = tmp_path / "text"
    text_dir.mkdir()
    payload = {
        "title": "Waste Collection",
        "source_file": "waste.pdf",
        "source_url": "https://d31atr86jnqrq2.cloudfront.net/docs/waste.pdf",
        "directory_url": "",
        "pages": [{"page": 2, "text": "Waste collection service details are listed here."}],
    }
    (text_dir / "waste.json").write_text(json.dumps(payload), encoding="utf-8")

    results = hybrid_search("When is my bin picked up?", vector_db_path=vector_path, text_directory=text_dir, limit=1)

    assert len(results) == 1
    assert "waste collection service" in results[0]["query_variants"][1]
    assert results[0]["metadata"]["title"] == "Waste Collection"


def test_hybrid_search_applies_reranker(monkeypatch, tmp_path):
    vector_path = tmp_path / "vector_db.json"
    first = _record("first", "First", "first text", [1.0, 0.0])
    second = _record("second", "Second", "second text", [0.8, 0.2])
    vector_path.write_text(json.dumps({"embedding_model": "test", "records": [first, second]}), encoding="utf-8")
    monkeypatch.setattr(
        "app.retrieval.search_vector_database",
        lambda question, path, limit: [
            {"score": 0.9, "text": first["text"], "metadata": first["metadata"]},
            {"score": 0.8, "text": second["text"], "metadata": second["metadata"]},
        ],
    )

    class ReverseReranker:
        def rerank(self, query, candidates, *, limit):
            ranked = list(reversed(candidates))[:limit]
            for index, candidate in enumerate(ranked, start=1):
                candidate["rerank_score"] = 100 - index
                candidate["rerank_rank"] = index
            return ranked

    results = hybrid_search("first second", vector_db_path=vector_path, text_directory=tmp_path, limit=1, reranker=ReverseReranker())

    assert results[0]["metadata"]["title"] == "Second"
    assert results[0]["rerank_rank"] == 1
