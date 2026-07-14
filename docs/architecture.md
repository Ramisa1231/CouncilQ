# Architecture

CouncilQ is a single advanced RAG assistant for City of Adelaide service questions. It is not a multi-skill agent. The system applies policy checks first, then retrieves trusted council source material, then renders a cited response or asks for clarification.

```mermaid
flowchart LR
  U["User request or JSON event"] --> N["normalize_event"]
  N --> P["policy_screen"]
  P -->|blocked| RB["respond_blocked"]
  P -->|requires_human_approval| H["request_human_approval"]
  H -->|human_approved| HA["respond_human_approved"]
  H -->|human_rejected| HR["respond_human_rejected"]
  P -->|continue| RET["retrieve_sources"]
  RET --> SEED["trusted source seeds"]
  SEED --> VDB["vector_db.json semantic retrieval"]
  VDB --> LEX["extracted-page lexical fallback"]
  RET -->|answered| RA["respond_answered"]
  RET -->|clarification_required| RC["respond_clarification_required"]
  RET -->|unsupported| RU["respond_unsupported"]

  RB --> OUT1["User response"]
  HA --> OUT2["User response"]
  HR --> OUT3["User response"]
  RA --> OUT4["User response"]
  RC --> OUT5["User response"]
  RU --> OUT6["User response"]
```

## Design Choices

- One assistant, one RAG pipeline.
- `normalize_event` accepts chat text, plain JSON `data`, and base64 Pub/Sub-style `data`.
- `policy_screen` runs before retrieval.
- Trusted URL seeds live in `data/seeds/trusted_sources.json`.
- PDF ingestion writes page-level JSON under `data/extracted/json/`.
- `vector_db.json` uses recursive character chunks with overlap, `thenlper/gte-small` embeddings, normalized vectors, cosine similarity, and preserved citation metadata.
- If no vector index exists, CouncilQ falls back to deterministic lexical matching over extracted page JSON records.
- Optional live page fetch is allowlisted and best-effort.
- Human approval uses ADK `RequestInput` and resumes through explicit approval/rejection routes.
- Quality gates are retrieval benchmarks, answer evals, and deterministic pytest coverage.
