import logging
from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory_agent.api.dependencies import require_event_service_token
from services.memory_agent.contracts.events import AgentEventEnvelope, EventReceipt
from services.memory_agent.database import get_db
from services.memory_agent.repositories.inbox import accept_event
from services.memory_agent.tasks.events import process_inbox_event_task

EventScheduler = Callable[[str], Awaitable[None]]

logger = logging.getLogger(__name__)
router = APIRouter()


async def schedule_accepted_event(event_id: str) -> None:
    try:
        process_inbox_event_task.delay(event_id=event_id)
    except Exception:
        logger.exception("Failed to enqueue accepted inbox event %s", event_id)


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
    row, created = await accept_event(db, envelope)
    await db.commit()

    if not created:
        response.status_code = status.HTTP_200_OK
        return EventReceipt(event_id=envelope.event_id, accepted=True, duplicate=True)

    await scheduler(row.event_id)
    return EventReceipt(event_id=envelope.event_id, accepted=True, duplicate=False)
