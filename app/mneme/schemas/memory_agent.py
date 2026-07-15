from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

AnswerMode = Literal[
    "kb_qa",
    "memory_query",
    "profile_query",
    "analysis_query",
    "general_chat",
]
MemoryAgentEventType = Literal[
    "document.projection.upserted",
    "document.memory.observed",
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

    @field_validator("occurred_at")
    @classmethod
    def occurred_at_must_have_timezone(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        return value


class DocumentChunkPayload(BaseModel):
    chunk_id: str
    chunk_index: int
    content: str
    content_hash: str
    page_no: int | None = None
    section_path: list[str] = Field(default_factory=list)


class DocumentProjectionPayload(BaseModel):
    projection_id: str
    document_id: str
    document_version: str
    file_name: str
    batch_index: int = Field(ge=0)
    batch_count: int = Field(gt=0)
    aggregate_hash: str
    chunks: list[DocumentChunkPayload]


class DocumentMemoryObservedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1, max_length=128)
    projection_id: str = Field(min_length=1, max_length=64)
    chunk_id: str = Field(min_length=1, max_length=128)
    document_version: str = Field(min_length=1, max_length=128)
    content_hash: str = Field(min_length=64, max_length=64)
    excerpt_hash: str = Field(min_length=64, max_length=64)
    observed_at: datetime
    excerpt: str = Field(min_length=1, max_length=20_000)


class EventReceipt(BaseModel):
    event_id: str
    accepted: bool
    duplicate: bool


class MemoryAgentAnswerRequest(BaseModel):
    request_id: str
    owner_id: int
    knowledge_base_id: str | None = None
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
