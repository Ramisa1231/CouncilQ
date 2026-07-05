# Architecture

CouncilQ uses a single-agent architecture.

```mermaid
flowchart TD
  User["User request"] --> Agent["CouncilQ ADK agent"]
  Agent --> Router["Skill routing"]
  Router --> Waste["waste_and_recycling skill"]
  Waste --> Policy["Policy guard"]
  Policy --> Structural["Structural policy check"]
  Structural --> Semantic["Semantic policy check"]
  Semantic --> Decision{"Approved?"}
  Decision -->|Yes| RAG["RAG retrieval"]
  Decision -->|Needs approval| Approval["Human approval"]
  Decision -->|No| Block["Policy violation"]
  RAG --> Answer["Source-cited answer"]
  Approval --> Answer
  Block --> Answer
```

## Design Choices

- Single agent by default.
- Skills provide modular procedural knowledge.
- Retrieval provides factual grounding.
- Policies are centralized.
- Evals define behavior before implementation.

