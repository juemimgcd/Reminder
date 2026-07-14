from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory_agent.contracts.events import AgentEventEnvelope
from services.memory_agent.models.inbox_event import InboxEvent


async def accept_event(db: AsyncSession, envelope: AgentEventEnvelope) -> tuple[InboxEvent, bool]:
    """Return (row, created); duplicate event_id returns the existing row and False."""
    insert_result = await db.execute(
        insert(InboxEvent)
        .values(
            event_id=envelope.event_id,
            payload=envelope.model_dump(mode="json"),
        )
        .on_conflict_do_nothing(index_elements=[InboxEvent.event_id])
        .returning(InboxEvent.id)
    )
    created = insert_result.scalar_one_or_none() is not None
    row = await db.scalar(select(InboxEvent).where(InboxEvent.event_id == envelope.event_id))
    if row is None:
        raise RuntimeError("accepted inbox event could not be loaded")
    return row, created
