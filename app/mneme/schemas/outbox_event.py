from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class OutboxEventData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    target_backend: str
    payload: dict[str, Any]
    idempotency_key: str
    status: str
    attempt_count: int
    max_attempts: int
    next_attempt_at: datetime | None = None
    locked_at: datetime | None = None
    processed_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime
