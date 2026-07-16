import asyncio
import logging
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.mneme.memoria.server.celery_app import celery_app
from app.mneme.memoria.server.config import settings
from app.mneme.memoria.server.database import engine, open_write_session
from app.mneme.memoria.server.models.inbox_event import InboxEvent
from app.mneme.memoria.server.observability.context import observation_context, safe_log
from app.mneme.memoria.server.repositories.runs import AnswerRunRepository
from app.mneme.memoria.server.services.event_dispatcher import EventProcessResult, dispatch_inbox_event

logger = logging.getLogger(__name__)
PENDING_EVENT_AGE = timedelta(seconds=30)
DEFAULT_PENDING_EVENT_BATCH_LIMIT = 100


@celery_app.task(name="memory_agent.process_event")
def process_inbox_event_task(event_id: str) -> dict[str, Any]:
    return asdict(asyncio.run(_process_inbox_event(event_id)))


async def _process_inbox_event(event_id: str) -> EventProcessResult:
    with observation_context(event_id=event_id):
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
                with observation_context(event_id=event_id):
                    safe_log(logger, logging.ERROR, "event_enqueue_failed")
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


@celery_app.task(name="memory_agent.fail_stale_answer_runs")
def fail_stale_answer_runs_task() -> int:
    return asyncio.run(_fail_stale_answer_runs_and_dispose())


async def _fail_stale_answer_runs_and_dispose() -> int:
    try:
        cutoff = datetime.now(UTC) - timedelta(seconds=settings.ANSWER_RUN_STALE_SECONDS)
        return await AnswerRunRepository().fail_stale(
            stale_before=cutoff,
            limit=settings.ANSWER_RUN_RECOVERY_BATCH_SIZE,
        )
    finally:
        await engine.dispose()
