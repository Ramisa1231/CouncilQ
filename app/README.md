# App

This directory contains the Google ADK-facing CouncilQ app.

The app uses the project `skills/` library as the capability registry:

- `policy_guard` checks requests before tools and retrieval.
- `waste_and_recycling` defines the first City of Adelaide service domain.

`app/agent.py` contains the implementation. The repository root `agent.py` re-exports `root_agent` so ADK can discover CouncilQ using the standard `my_agent/agent.py` project layout.
