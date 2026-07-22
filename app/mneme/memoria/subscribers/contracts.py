from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

SubscriberActionType = Literal[
    "create_approval",
    "add_context_candidate",
    "send_notification",
]
SubscriberDispatchStatus = Literal["succeeded", "failed", "timed_out", "rejected"]


class RuntimeSubscriberEvent(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=128)
    user_id: int = Field(gt=0)
    run_id: str | None = Field(default=None, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=512)
    payload: dict[str, Any] = Field(default_factory=dict)


class SubscriberAction(BaseModel):
    type: SubscriberActionType
    payload: dict[str, Any] = Field(default_factory=dict)


class SubscriberDispatchResult(BaseModel):
    subscriber_name: str
    status: SubscriberDispatchStatus
    duration_ms: int = Field(ge=0)
    action_count: int = Field(default=0, ge=0)
    error_type: str | None = None


class RuntimeSubscriber(Protocol):
    name: str
    event_types: frozenset[str]
    timeout_seconds: float

    async def handle(self, event: RuntimeSubscriberEvent) -> list[SubscriberAction]: ...
