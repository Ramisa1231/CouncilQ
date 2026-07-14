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
  RET --> SEED["trusted source seed lookup"]
  RET --> QUERY["document query expansion"]
  QUERY --> DENSE["dense vector search<br/>(when vector_db.json exists)"]
  QUERY --> LEX["lexical search<br/>(vector records or extracted pages)"]
  DENSE --> FUSION["RRF fusion"]
  LEX --> FUSION
  FUSION --> RERANK["rerank + compress context"]
  SEED --> GROUND["grounding validation"]
  RERANK --> GROUND
  GROUND -->|answered| RA["respond_answered"]
  GROUND -->|clarification_required| RC["respond_clarification_required"]
  GROUND -->|unsupported| RU["respond_unsupported"]

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
- Trusted URL seeds live in `data/seeds/trusted_sources.json` and handle known service questions before document fallback is needed.
- PDF ingestion writes page-level JSON under `data/extracted/json/`.
- `vector_db.json` uses recursive character chunks with overlap, `thenlper/gte-small` embeddings, normalized vectors, cosine similarity, and preserved citation metadata.
- Document retrieval expands citizen wording deterministically, runs dense vector search when `vector_db.json` is available, runs lexical search over vector records or extracted page JSON, fuses candidates with Reciprocal Rank Fusion, reranks fused candidates, and compresses snippets before citation formatting.
- If no vector index exists, lexical document search reads extracted page JSON records directly.
- Runtime retrieval events are appended to `data/indexes/retrieval_logs.jsonl` as a side effect for debugging and benchmark triage.
- Optional live page fetch is allowlisted and best-effort.
- Human approval uses ADK `RequestInput` and resumes through explicit approval/rejection routes.
- Quality gates are retrieval benchmarks, answer evals, and deterministic pytest coverage.
