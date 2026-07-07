 # Architecture

 CouncilQ uses a single-agent architecture. The diagram below mirrors the implemented MVP workflow in the repository: user request classification, policy screening, deterministic trusted-source routing for waste/recycling, and response generation with clear branching for blocked, human-approval, and continue paths. A secondary swimlane shows planned next increments.

 ```mermaid
 flowchart LR
   subgraph user_flow [User -> Agent]
     U["User request"] --> C[classify_request<br/><i>classify user intent</i>]
   end

   subgraph core_agent [CouncilQ ADK agent]
     direction TB
     C --> S["respond_with_skills<br/>(skill registry)"]
     C --> P["policy_screen<br/>(Policy & Safety Guard)"]

     P --> PS1["structural_policy_check"]
     PS1 --> PS2["semantic_policy_check"]
     PS2 --> DEC{"Decision"}

     DEC -->|blocked| RB["respond_blocked<br/>(Policy blocked)"]
     DEC -->|requires_human_approval| RH["respond_requires_human_approval<br/>(Human approval)"]
     DEC -->|continue| RET["retrieve_sources<br/>(deterministic source routing)"]

     RET -->|answered| RA["respond_answered<br/>(Answer with sources)"]
     RET -->|clarification_required| RC["respond_clarification_required<br/>(Ask for clarification)"]
     RET -->|unsupported| RU["respond_unsupported<br/>(AI unsupported)"]
   end

   %% show connections to final responses
   RB --> OUT1["User response"]
   RH --> OUT2["User response"]
   RA --> OUT3["User response"]
   RC --> OUT4["User response"]
   RU --> OUT5["User response"]

   %% Skill hints / notes
   classDef skill fill:#e6ffed,stroke:#2d8a4d;
   class S skill

   %% Next increments (roadmap)
   subgraph next [Next increments]
     direction LR
     A1["LLM Answer Review<br/>(Pydantic output_schema)"]
     A2["Expanded Council Domains<br/>(beyond waste/recycling)"]
     A3["Deeper Retrieval Stack<br/>(semantic retrieval/ranking)"]
     A4["LLM-graded Behavior Evals<br/>(beyond deterministic harness)"]
     A1 --> A2 --> A3 --> A4
   end
 ```

 ## Design choices

 - Single agent by default; skills provide modular, testable procedures.
 - Current retrieval is deterministic trusted-source routing for MVP waste/recycling support.
 - Optional live page fetch is allowlisted and best-effort; if unavailable, CouncilQ falls back to curated trusted links.
 - A central policy guard performs structural and semantic checks and returns an explicit decision (block, requires_human_approval, sanitize_and_continue/continue).
 - Workflow is evaluation-first: specs, tests, and evals drive changes before implementation.
