from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory_agent.contracts.events import AgentEventEnvelope, DocumentProjectionPayload
from services.memory_agent.database import engine
from services.memory_agent.models.inbox_event import InboxEvent
from services.memory_agent.services.projections import finalize_projection, stage_projection_batch

EventProcessStatus = Literal["succeeded", "skipped", "not_found"]
EventHandler = Callable[[AgentEventEnvelope], Awaitable[None]]


@dataclass(frozen=True)
class EventProcessResult:
    event_id: str
    status: EventProcessStatus


async def handle_document_projection_upserted(event: AgentEventEnvelope) -> None:
    payload = DocumentProjectionPayload.model_validate(event.payload)
    receipt = await stage_projection_batch(
        payload,
        owner_id=event.owner_id,
        knowledge_base_id=event.knowledge_base_id,
    )
    if receipt.is_final_batch:
        await finalize_projection(receipt.projection_id)


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
    async with engine.connect() as connection:
        acquired = await connection.scalar(
            text("SELECT pg_try_advisory_lock(hashtextextended(:event_id, 1))"),
            {"event_id": event_id},
        )
        await connection.commit()
        if not acquired:
            return EventProcessResult(event_id=event_id, status="skipped")
        try:
            async with AsyncSession(bind=connection, expire_on_commit=False) as session:
                async with session.begin():
                    row = await session.scalar(
                        select(InboxEvent)
                        .where(InboxEvent.event_id == event_id)
                        .with_for_update()
                    )
                    if row is None:
                        return EventProcessResult(event_id=event_id, status="not_found")
                    if row.status != "pending":
                        return EventProcessResult(event_id=event_id, status="skipped")
                    row.attempt_count += 1
                    row.last_error = None
                    event = AgentEventEnvelope.model_validate(row.payload)

                try:
                    handler = EVENT_HANDLERS[event.event_type]
                    await handler(event)
                except Exception as exc:
                    async with session.begin():
                        row = await session.scalar(
                            select(InboxEvent)
                            .where(InboxEvent.event_id == event_id)
                            .with_for_update()
                        )
                        if row is not None and row.status == "pending":
                            row.last_error = str(exc)[:2000]
                    raise

                async with session.begin():
                    row = await session.scalar(
                        select(InboxEvent)
                        .where(InboxEvent.event_id == event_id)
                        .with_for_update()
                    )
                    if row is not None and row.status == "pending":
                        row.status = "succeeded"
                        row.processed_at = datetime.now(UTC)
                return EventProcessResult(event_id=event_id, status="succeeded")
        finally:
            await connection.execute(
                text("SELECT pg_advisory_unlock(hashtextextended(:event_id, 1))"),
                {"event_id": event_id},
            )
            await connection.commit()
