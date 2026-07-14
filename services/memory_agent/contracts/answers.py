from typing import Any

from pydantic import BaseModel, Field

from services.memory_agent.contracts.common import AnswerMode, ModelInvocationConfig


class AnswerRequest(BaseModel):
    request_id: str
    owner_id: int
    knowledge_base_id: str | None = None
    session_id: str | None = None
    message_id: str
    question: str = Field(min_length=1)
    answer_mode: AnswerMode
    top_k: int = Field(default=4, ge=1, le=10)
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
