from datetime import datetime
from typing import Literal

from pydantic import BaseModel

MemoryType = Literal[
    "preference",
    "profile_fact",
    "project_context",
    "decision",
    "goal",
    "constraint",
]
MemoryStatus = Literal["active", "superseded", "invalidated"]


class MemoryData(BaseModel):
    memory_id: str
    owner_id: int
    knowledge_base_id: str | None = None
    memory_type: MemoryType
    subject: str
    predicate: str
    value: str
    confidence: float
    status: MemoryStatus
    created_at: datetime
    updated_at: datetime
