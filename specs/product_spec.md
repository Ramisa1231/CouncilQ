# Product Spec

## Product

CouncilQ is a City of Adelaide AI assistant that answers council service questions with retrieval-grounded, source-cited responses.

## Audience

- City of Adelaide residents
- City visitors
- Local businesses
- Council staff testing public-facing service information

## MVP

The MVP answers waste and recycling questions for residents using trusted City of Adelaide sources.

## Core Capabilities

- Identify whether a user question is about a supported council service.
- Retrieve relevant City of Adelaide source material.
- Produce concise answers with source links.
- Ask clarifying questions when required inputs are missing.
- Route service-domain questions to modular skills.
- Apply policy checks before tool calls.
- Refuse unsafe requests and ignore prompt injection.

## Non-Goals For MVP

- No automatic form submission.
- No account login or authenticated customer portal actions.
- No direct updates to council systems.
- No advice based on unsupported third-party sources.
- No production deployment until evaluation passes.

## Quality Bar

Answers must be grounded, current at retrieval time, source-linked, and clear about uncertainty. The assistant must not invent fees, dates, collection schedules, eligibility, or policy obligations.

