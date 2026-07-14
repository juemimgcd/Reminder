from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import select

from services.memory_agent.contracts.events import AgentEventEnvelope
from services.memory_agent.database import open_write_session
from services.memory_agent.models.inbox_event import InboxEvent

EventProcessStatus = Literal["succeeded", "skipped", "not_found"]
EventHandler = Callable[[AgentEventEnvelope], Awaitable[None]]


@dataclass(frozen=True)
class EventProcessResult:
    event_id: str
    status: EventProcessStatus


async def handle_document_projection_upserted(event: AgentEventEnvelope) -> None:
    pass


async def handle_document_deleted(event: AgentEventEnvelope) -> None:
    pass


async def handle_knowledge_base_deleted(event: AgentEventEnvelope) -> None:
    pass


async def handle_conversation_completed(event: AgentEventEnvelope) -> None:
    pass


async def handle_conversation_deleted(event: AgentEventEnvelope) -> None:
    pass


async def handle_user_memory_requested(event: AgentEventEnvelope) -> None:
    pass


async def handle_user_memory_settings_changed(event: AgentEventEnvelope) -> None:
    pass


EVENT_HANDLERS: dict[str, EventHandler] = {
    "document.projection.upserted": handle_document_projection_upserted,
    "document.deleted": handle_document_deleted,
    "knowledge_base.deleted": handle_knowledge_base_deleted,
    "conversation.completed": handle_conversation_completed,
    "conversation.deleted": handle_conversation_deleted,
    "user.memory_requested": handle_user_memory_requested,
    "user.memory_settings.changed": handle_user_memory_settings_changed,
}


async def dispatch_inbox_event(event_id: str) -> EventProcessResult:
    processing_error: Exception | None = None

    async with open_write_session() as session:
        row = await session.scalar(
            select(InboxEvent).where(InboxEvent.event_id == event_id).with_for_update()
        )
        if row is None:
            return EventProcessResult(event_id=event_id, status="not_found")
        if row.status != "pending":
            return EventProcessResult(event_id=event_id, status="skipped")

        row.status = "running"
        row.attempt_count += 1
        row.last_error = None

        try:
            event = AgentEventEnvelope.model_validate(row.payload)
            handler = EVENT_HANDLERS[event.event_type]
            await handler(event)
        except Exception as exc:
            row.status = "pending"
            row.last_error = str(exc)[:2000]
            processing_error = exc
        else:
            row.status = "succeeded"
            row.processed_at = datetime.now(UTC)

    if processing_error is not None:
        raise processing_error
    return EventProcessResult(event_id=event_id, status="succeeded")
