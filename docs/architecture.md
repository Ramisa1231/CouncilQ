# Architecture

CouncilQ uses a single-agent ADK 2.0 workflow with modular Day 3 skills. The graph normalizes incoming chat or event payloads, classifies the request, applies policy checks, routes to deterministic trusted-source support for the current MVP, and renders a grounded response.

```mermaid
flowchart LR
  subgraph input [Input]
    U["User request or JSON event"] --> N["normalize_event<br/><i>chat, plain JSON, or base64 data</i>"]
  end

  subgraph workflow [CouncilQ ADK Workflow]
    direction TB
    N --> C["classify_request<br/><i>intent routing</i>"]
    C -->|skills| S["respond_with_skills"]
    C -->|council_question| P["policy_screen<br/><i>policy_guard</i>"]

    P -->|blocked| RB["respond_blocked"]
    P -->|requires_human_approval| H["request_human_approval<br/><i>ADK RequestInput</i>"]
    H -->|human_approved| HA["respond_human_approved"]
    H -->|human_rejected| HR["respond_human_rejected"]
    P -->|continue| RET["retrieve_sources<br/><i>deterministic source routing</i>"]

    RET -->|answered| RA["respond_answered"]
    RET -->|clarification_required| RC["respond_clarification_required"]
    RET -->|unsupported| RU["respond_unsupported"]
  end

  RB --> OUT1["User response"]
  HA --> OUT2["User response"]
  HR --> OUT3["User response"]
  RA --> OUT4["User response"]
  RC --> OUT5["User response"]
  RU --> OUT6["User response"]

  subgraph roadmap [Next Increments]
    direction LR
    A1["LLM Answer Review<br/>(Pydantic output_schema)"]
    A2["Expanded Council Domains<br/>(beyond waste/recycling)"]
    A3["Deeper Retrieval Stack<br/>(semantic retrieval/ranking)"]
    A4["LLM-graded Behavior Evals<br/>(beyond deterministic harness)"]
    A1 --> A2 --> A3 --> A4
  end
```

## Design Choices

- Single agent by default; skills provide modular, testable procedures.
- `normalize_event` accepts chat text, plain JSON `data`, and base64 Pub/Sub-style `data`.
- Current retrieval is deterministic trusted-source routing for MVP waste/recycling support.
- Optional live page fetch is allowlisted and best-effort; if unavailable, CouncilQ falls back to curated trusted links.
- `policy_screen` runs before retrieval or any higher-risk workflow branch.
- Human approval uses ADK `RequestInput` and resumes through explicit approval/rejection routes.
- Workflow changes are covered by deterministic pytest checks; broader conversational behavior belongs in `agents-cli eval`.
