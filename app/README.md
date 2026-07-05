# App

This directory contains helper modules for the Google ADK-facing CouncilQ app.

The app uses the project `skills/` library as the capability registry:

- `policy_guard` checks requests before tools and retrieval.
- `waste_and_recycling` defines the first City of Adelaide service domain.

The only ADK agent entry file is the repository root `agent.py`, so ADK can discover CouncilQ using the standard `my_agent/agent.py` project layout. Helper modules in this folder provide tools, policy checks, skill loading, and source lookup.
