from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

EventType = Literal[
    "document.projection.upserted",
    "document.deleted",
    "knowledge_base.deleted",
    "conversation.completed",
    "conversation.deleted",
    "user.memory_requested",
    "user.memory_settings.changed",
]


class AgentEventEnvelope(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    event_type: EventType
    schema_version: Literal["1"] = "1"
    occurred_at: datetime
    owner_id: int
    knowledge_base_id: str | None = None
    payload: dict[str, Any]


class EventReceipt(BaseModel):
    event_id: str
    accepted: bool
    duplicate: bool


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
