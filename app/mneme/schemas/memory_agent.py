from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, SecretStr

AnswerMode = Literal[
    "kb_qa",
    "memory_query",
    "profile_query",
    "analysis_query",
    "general_chat",
]
MemoryAgentEventType = Literal[
    "document.projection.upserted",
    "document.deleted",
    "knowledge_base.deleted",
    "conversation.completed",
    "conversation.deleted",
    "user.memory_requested",
    "user.memory_settings.changed",
]


class ModelInvocationConfig(BaseModel):
    provider: str
    base_url: str
    model_name: str
    api_key: SecretStr = Field(exclude=True)
    temperature: float = 0.0


class MemoryAgentEvent(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    event_type: MemoryAgentEventType
    schema_version: Literal["1"] = "1"
    occurred_at: datetime
    owner_id: int
    knowledge_base_id: str | None = None
    payload: dict[str, Any]


class EventReceipt(BaseModel):
    event_id: str
    accepted: bool
    duplicate: bool


class MemoryAgentAnswerRequest(BaseModel):
    request_id: str
    owner_id: int
    knowledge_base_id: str
    session_id: str | None = None
    message_id: str
    question: str = Field(min_length=1)
    answer_mode: AnswerMode
    top_k: int = Field(default=4, ge=1, le=10)
    model: ModelInvocationConfig | None = Field(default=None, exclude=True)


class MemoryAgentAnswerResponse(BaseModel):
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
