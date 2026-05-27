from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.models.outbox_event import OutboxEvent


async def create_outbox_event(
        db: AsyncSession,
        *,
        event_id: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        target_backend: str,
        payload: dict[str, Any],
        idempotency_key: str,
        status: str = "pending",
        max_attempts: int = 3,
) -> OutboxEvent:
    event = OutboxEvent(
        id=event_id,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        target_backend=target_backend,
        payload=payload,
        idempotency_key=idempotency_key,
        status=status,
        max_attempts=max_attempts,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


async def get_outbox_event_by_id(
        db: AsyncSession,
        *,
        event_id: str,
) -> OutboxEvent | None:
    result = await db.execute(
        select(OutboxEvent).where(OutboxEvent.id == event_id)
    )
    return result.scalar_one_or_none()


async def get_outbox_event_by_idempotency_key(
        db: AsyncSession,
        *,
        idempotency_key: str,
) -> OutboxEvent | None:
    result = await db.execute(
        select(OutboxEvent).where(OutboxEvent.idempotency_key == idempotency_key)
    )
    return result.scalar_one_or_none()


async def list_dispatchable_outbox_events(
        db: AsyncSession,
        *,
        limit: int = 20,
        target_backend: str | None = None,
        now: datetime | None = None,
) -> list[OutboxEvent]:
    sql = select(OutboxEvent).where(
        OutboxEvent.status.in_(["pending", "failed"])
    )
    if now is not None:
        sql = sql.where(
            or_(
                OutboxEvent.next_attempt_at.is_(None),
                OutboxEvent.next_attempt_at <= now,
            )
        )
    if target_backend:
        sql = sql.where(OutboxEvent.target_backend == target_backend)

    sql = sql.order_by(OutboxEvent.created_at.asc()).limit(limit)
    result = await db.execute(sql)
    return list(result.scalars().all())


async def update_outbox_event_status(
        db: AsyncSession,
        *,
        event_id: str,
        status: str,
        attempt_count: int | None = None,
        next_attempt_at: datetime | None = None,
        locked_at: datetime | None = None,
        processed_at: datetime | None = None,
        last_error: str | None = None,
        clear_error: bool = False,
) -> OutboxEvent | None:
    event = await get_outbox_event_by_id(db, event_id=event_id)
    if not event:
        return None

    event.status = status
    if attempt_count is not None:
        event.attempt_count = attempt_count
    if next_attempt_at is not None or status in {"pending", "running", "succeeded", "dead_letter"}:
        event.next_attempt_at = next_attempt_at
    if locked_at is not None or status in {"pending", "failed", "succeeded", "dead_letter"}:
        event.locked_at = locked_at
    if processed_at is not None:
        event.processed_at = processed_at
    if clear_error:
        event.last_error = None
    elif last_error is not None:
        event.last_error = last_error

    await db.flush()
    await db.refresh(event)
    return event
