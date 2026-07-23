from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .tools import answer_council_question


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    council: str = Field(default="City of Adelaide")
    fetch_live_pages: bool = Field(default=True)


class AskResponse(BaseModel):
    trace_id: str
    status: str
    answer: str
    sources: list[dict[str, str]]
    policy: dict[str, Any]
    live_retrieval: dict[str, Any]


app = FastAPI(title="CouncilQ API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    result = answer_council_question(
        question=request.question,
        council=request.council,
        fetch_live_pages=request.fetch_live_pages,
    )
    return AskResponse.model_validate(result)
