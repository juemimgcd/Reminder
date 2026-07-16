from typing import Any, Literal

from pydantic import BaseModel, Field

from app.mneme.memoria.server.contracts.common import AnswerMode, ModelInvocationConfig


class AnswerRequest(BaseModel):
    request_id: str
    trace_id: str = Field(default="", max_length=64)
    owner_id: int
    knowledge_base_id: str | None = None
    session_id: str | None = None
    message_id: str
    question: str = Field(min_length=1)
    answer_mode: AnswerMode
    top_k: int = Field(default=4, ge=1, le=10)
    allow_model_fallback: bool = False
    model: ModelInvocationConfig | None = Field(default=None, exclude=True)


class AnswerResponse(BaseModel):
    answer: str
    mode: AnswerMode
    route: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float
    uncertainty: str | None = None
    insufficient_evidence: bool = False
    memory_ids: list[str] = Field(default_factory=list)
    document_ids: list[str] = Field(default_factory=list)
    run_id: str


class AnswerStreamEvent(BaseModel):
    type: Literal["phase", "final", "error"]
    run_id: str | None = None
    phase: str | None = None
    status: str | None = None
    code: str | None = None
    response: AnswerResponse | None = None
