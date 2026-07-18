from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.memoria.events import AgentEvent
from app.mneme.memoria.models.automation import DurableAgentRun
from app.mneme.memoria.models.runtime_event import AgentRuntimeEvent
from app.mneme.memoria.run_models import AgentStoredEvent


async def append_durable_runtime_event(
    db: AsyncSession,
    *,
    run_id: str,
    event: AgentEvent,
) -> AgentStoredEvent:
    run = await db.scalar(
        select(DurableAgentRun)
        .where(DurableAgentRun.run_id == run_id)
        .with_for_update()
    )
    if run is None:
        raise RuntimeError("durable agent run not found for event")

    sequence = int(run.last_event_sequence or 0) + 1
    delivered = event.with_delivery(run_id=run_id, sequence=sequence)
    db.add(
        AgentRuntimeEvent(
            id=f"event_{uuid4().hex}",
            event_type=delivered.name.value,
            schema_version=delivered.schema_version,
            sequence=sequence,
            agent_role=delivered.agent_role,
            phase=delivered.phase or None,
            occurred_at=delivered.created_at,
            trace_id=_metadata_string(delivered, "trace_id") or run.trace_id,
            run_id=run_id,
            session_id=run.session_id,
            user_id=run.user_id,
            loop_index=_metadata_int(delivered, "loop_index"),
            tool_call_id=_metadata_string(delivered, "tool_call_id"),
            duration_ms=_metadata_int(delivered, "duration_ms"),
            input_tokens=_metadata_int(delivered, "input_tokens"),
            output_tokens=_metadata_int(delivered, "output_tokens"),
            error_kind=_metadata_string(delivered, "error_kind")
            or _metadata_string(delivered, "error_type"),
            selected_capability_ids=_metadata_string_list(
                delivered,
                "selected_capability_ids",
            ),
            payload=delivered.to_stream_dict(),
        )
    )
    run.last_event_sequence = sequence
    run.last_event_id = str(sequence)
    await db.flush()
    return AgentStoredEvent(event_id=str(sequence), event=delivered)


async def list_durable_runtime_events(
    db: AsyncSession,
    *,
    run_id: str,
    after_sequence: int = 0,
) -> list[AgentStoredEvent]:
    result = await db.execute(
        select(AgentRuntimeEvent)
        .where(
            AgentRuntimeEvent.run_id == run_id,
            AgentRuntimeEvent.sequence.is_not(None),
            AgentRuntimeEvent.sequence > after_sequence,
        )
        .order_by(AgentRuntimeEvent.sequence)
    )
    events: list[AgentStoredEvent] = []
    for row in result.scalars():
        event = AgentEvent.model_validate(row.payload)
        sequence = int(row.sequence)
        if event.sequence != sequence or event.run_id != run_id:
            event = event.model_copy(
                update={
                    "run_id": run_id,
                    "sequence": sequence,
                    "created_at": row.occurred_at,
                }
            )
        events.append(AgentStoredEvent(event_id=str(sequence), event=event))
    return events


def parse_event_sequence(value: str | None) -> int:
    if not value:
        return 0
    major = value.partition("-")[0]
    try:
        sequence = int(major)
    except (TypeError, ValueError):
        raise ValueError("event cursor must be a positive integer") from None
    if sequence < 0:
        raise ValueError("event cursor must be a positive integer")
    return sequence


def _metadata_string(event: AgentEvent, key: str) -> str | None:
    value = event.metadata.get(key)
    return value if isinstance(value, str) and value else None


def _metadata_int(event: AgentEvent, key: str) -> int | None:
    value = event.metadata.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _metadata_string_list(event: AgentEvent, key: str) -> list[str]:
    value = event.metadata.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
