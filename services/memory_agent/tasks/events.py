import asyncio
import logging
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from services.memory_agent.celery_app import celery_app
from services.memory_agent.database import engine, open_write_session
from services.memory_agent.models.inbox_event import InboxEvent
from services.memory_agent.services.event_dispatcher import EventProcessResult, dispatch_inbox_event

logger = logging.getLogger(__name__)
PENDING_EVENT_AGE = timedelta(seconds=30)
DEFAULT_PENDING_EVENT_BATCH_LIMIT = 100


@celery_app.task(name="memory_agent.process_event")
def process_inbox_event_task(event_id: str) -> dict[str, Any]:
    return asdict(asyncio.run(_process_inbox_event(event_id)))


async def _process_inbox_event(event_id: str) -> EventProcessResult:
    try:
        return await dispatch_inbox_event(event_id)
    finally:
        await engine.dispose()


async def _dispatch_pending_events(batch_limit: int) -> int:
    cutoff = datetime.now(UTC) - PENDING_EVENT_AGE
    limit = min(max(batch_limit, 1), DEFAULT_PENDING_EVENT_BATCH_LIMIT)
    enqueued = 0

    async with open_write_session() as session:
        event_ids = list(
            await session.scalars(
                select(InboxEvent.event_id)
                .where(InboxEvent.status == "pending", InboxEvent.received_at <= cutoff)
                .order_by(InboxEvent.received_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        for event_id in event_ids:
            try:
                process_inbox_event_task.delay(event_id=event_id)
            except Exception:
                logger.exception("Failed to enqueue pending inbox event %s", event_id)
            else:
                enqueued += 1

    return enqueued


@celery_app.task(name="memory_agent.dispatch_pending_events")
def dispatch_pending_events_task(batch_limit: int = DEFAULT_PENDING_EVENT_BATCH_LIMIT) -> int:
    return asyncio.run(_dispatch_pending_events_and_dispose(batch_limit))


async def _dispatch_pending_events_and_dispose(batch_limit: int) -> int:
    try:
        return await _dispatch_pending_events(batch_limit)
    finally:
        await engine.dispose()
