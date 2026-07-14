# App Modules

`app/` contains the runtime code for the single CouncilQ advanced RAG assistant.

- `api.py`: FastAPI surface.
- `workflow_nodes.py`: ADK workflow nodes.
- `policy.py`: policy, PII, prompt-injection, and tool-approval checks.
- `answer.py`: final answer formatting.
- `grounding.py`: citation and source trust validation.
- `query_rewrite.py`: deterministic query expansion hooks.
- `context_compression.py`: extractive context compression helpers.
- `rerank.py`: reranking interface and deterministic fallback.
- `retrieval.py`: public RAG pipeline entrypoints.
- `rag.py`: trusted source retrieval and document fallback logic.
- `vector_db.py`: local JSON vector index build/search helpers.
- `document_ingestion.py`: PDF discovery, download, extraction, and chunking.
- `tools.py`: compatibility wrapper around the RAG pipeline.
