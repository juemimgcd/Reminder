import logging
from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.memoria.server.api.dependencies import require_event_service_token
from app.mneme.memoria.server.contracts.events import AgentEventEnvelope, EventReceipt
from app.mneme.memoria.server.database import get_db
from app.mneme.memoria.server.observability.context import observation_context, safe_log
from app.mneme.memoria.server.repositories.inbox import accept_event
from app.mneme.memoria.server.tasks.events import process_inbox_event_task

EventScheduler = Callable[[str], Awaitable[None]]

logger = logging.getLogger(__name__)
router = APIRouter()


async def schedule_accepted_event(event_id: str) -> None:
    try:
        process_inbox_event_task.delay(event_id=event_id)
    except Exception:
        with observation_context(event_id=event_id):
            safe_log(logger, logging.ERROR, "event_enqueue_failed")


def get_event_scheduler() -> EventScheduler:
    return schedule_accepted_event


@router.post("/events", response_model=EventReceipt, status_code=status.HTTP_202_ACCEPTED)
async def receive_event(
    envelope: AgentEventEnvelope,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    _claims: Annotated[dict[str, Any], Depends(require_event_service_token)],
    scheduler: Annotated[EventScheduler, Depends(get_event_scheduler)],
) -> EventReceipt:
    with observation_context(event_id=envelope.event_id):
        row, created = await accept_event(db, envelope)
        await db.commit()

        if not created:
            response.status_code = status.HTTP_200_OK
            return EventReceipt(event_id=envelope.event_id, accepted=True, duplicate=True)

        await scheduler(row.event_id)
        return EventReceipt(event_id=envelope.event_id, accepted=True, duplicate=False)
