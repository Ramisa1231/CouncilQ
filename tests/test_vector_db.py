import json
import math

from app.vector_db import build_vector_database, search_vector_database


class KeywordEmbedder:
    model_name = "test-keyword-embedder"

    def embed(self, texts):
        vectors = []
        for text in texts:
            lowered = text.lower()
            vectors.append(
                [
                    float("privacy" in lowered or "personal information" in lowered),
                    float("procurement" in lowered),
                    float("waste" in lowered),
                ]
            )
        return vectors


def test_build_vector_database_writes_normalized_json(tmp_path):
    text_dir = tmp_path / "text"
    text_dir.mkdir()
    output_path = tmp_path / "vector_db.json"
    payload = {
        "title": "Privacy Policy",
        "source_file": "privacy-policy.pdf",
        "source_url": "https://d31atr86jnqrq2.cloudfront.net/docs/privacy-policy.pdf",
        "directory_url": "https://www.cityofadelaide.com.au/about-council/plans-reporting/strategies-plans-policies/",
        "pages": [
            {
                "page": 4,
                "text": "Privacy and personal information handling for City of Adelaide services.",
                "content_hash": "abc",
            }
        ],
    }
    (text_dir / "privacy-policy.json").write_text(json.dumps(payload), encoding="utf-8")

    vector_db = build_vector_database(
        text_directory=text_dir,
        output_path=output_path,
        embedder=KeywordEmbedder(),
        chunk_size=1000,
        chunk_overlap=100,
    )

    assert output_path.exists()
    assert vector_db["schema_version"] == 1
    assert vector_db["embedding_model"] == "test-keyword-embedder"
    assert vector_db["distance"] == "cosine"
    assert vector_db["normalized_embeddings"] is True
    assert vector_db["chunking"]["method"] == "recursive_character"
    assert vector_db["record_count"] == 1
    record = vector_db["records"][0]
    assert record["metadata"]["title"] == "Privacy Policy"
    assert record["metadata"]["page"] == 4
    assert math.isclose(sum(value * value for value in record["embedding"]), 1.0)


def test_search_vector_database_returns_nearest_chunks(tmp_path):
    vector_db = {
        "schema_version": 1,
        "embedding_model": "test-keyword-embedder",
        "distance": "cosine",
        "normalized_embeddings": True,
        "chunking": {"method": "recursive_character", "chunk_size": 1000, "chunk_overlap": 100},
        "record_count": 2,
        "records": [
            {
                "id": "privacy",
                "text": "Privacy and personal information.",
                "embedding": [1.0, 0.0, 0.0],
                "metadata": {
                    "title": "Privacy Policy",
                    "source": "privacy-policy.pdf",
                    "source_url": "https://d31atr86jnqrq2.cloudfront.net/docs/privacy-policy.pdf",
                    "directory_url": "",
                    "page": 4,
                    "chunk_id": 0,
                    "start_index": 0,
                    "content_hash": "abc",
                },
            },
            {
                "id": "procurement",
                "text": "Procurement policy.",
                "embedding": [0.0, 1.0, 0.0],
                "metadata": {
                    "title": "Procurement Policy",
                    "source": "procurement-policy.pdf",
                    "source_url": "https://d31atr86jnqrq2.cloudfront.net/docs/procurement-policy.pdf",
                    "directory_url": "",
                    "page": 2,
                    "chunk_id": 0,
                    "start_index": 0,
                    "content_hash": "def",
                },
            },
        ],
    }
    path = tmp_path / "vector_db.json"
    path.write_text(json.dumps(vector_db), encoding="utf-8")

    results = search_vector_database(
        "How is personal information handled?",
        path=path,
        embedder=KeywordEmbedder(),
        limit=1,
    )

    assert len(results) == 1
    assert results[0]["metadata"]["title"] == "Privacy Policy"
    assert results[0]["score"] > 0.9
