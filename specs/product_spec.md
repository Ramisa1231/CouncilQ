# Product Spec

## Product

CouncilQ is a City of Adelaide advanced RAG assistant that answers council service questions with retrieval-grounded, source-cited responses.

## Audience

- City of Adelaide residents
- City visitors
- Local businesses
- Council staff testing public-facing service information

## MVP

The MVP answers waste and recycling questions and can retrieve from trusted ingested council documents when available.

## Core Capabilities

- Apply policy checks before retrieval.
- Retrieve relevant City of Adelaide source material.
- Use trusted source seeds, ingested PDF pages, and a local vector index.
- Produce concise answers with source links.
- Ask clarifying questions when required inputs are missing.
- Refuse unsafe requests and ignore prompt injection.

## Non-Goals For MVP

- No automatic form submission.
- No account login or authenticated customer portal actions.
- No direct updates to council systems.
- No advice based on unsupported third-party sources.
- No runtime multi-skill dispatch.
- No production deployment until evaluation passes.

## Quality Bar

Answers must be grounded, current at retrieval time where needed, source-linked, and clear about uncertainty. The assistant must not invent fees, dates, collection schedules, eligibility, or policy obligations.
