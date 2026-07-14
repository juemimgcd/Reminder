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
