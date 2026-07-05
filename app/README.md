# App

This directory contains the Google ADK-facing CouncilQ app.

The app uses the project `skills/` library as the capability registry:

- `policy_guard` checks requests before tools and retrieval.
- `waste_and_recycling` defines the first City of Adelaide service domain.

`agent.py` exposes `root_agent` for ADK.
