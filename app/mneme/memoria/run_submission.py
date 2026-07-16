from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.memoria.events import AgentEvent
from app.mneme.memoria.persistence.automation import create_or_get_durable_run, durable_run_to_record
from app.mneme.memoria.persistence.runs import agent_run_store
from app.mneme.memoria.run_models import TERMINAL_AGENT_RUN_STATUSES, AgentRunRecord, AgentRunStatus


async def submit_agent_run(db: AsyncSession, record: AgentRunRecord) -> tuple[AgentRunRecord, bool]:
    """Persist the run before publishing it to Redis/Celery.

    The explicit commit is the durability boundary: a broker-visible task must
    never exist without a recoverable PostgreSQL run record.
    """
    durable, durable_created = await create_or_get_durable_run(db, record)
    durable_record = durable_run_to_record(durable)
    await db.commit()
    if durable_record.status in TERMINAL_AGENT_RUN_STATUSES:
        if await agent_run_store.get(durable_record.run_id) is None:
            await agent_run_store.create(durable_record)
        return durable_record, False
    cached_record, cache_created = await agent_run_store.create_or_get_and_enqueue(durable_record)
    created = durable_created and cache_created
    if cache_created:
        await agent_run_store.append_event(
            cached_record.run_id,
            AgentEvent.lifecycle(
                "queued",
                trace_id=cached_record.trace_id,
                run_id=cached_record.run_id,
                session_id=cached_record.session_id,
                user_id=cached_record.user_id,
                loop_index=0,
                loop_reason="session_fifo",
            ),
        )
    if cached_record.status == AgentRunStatus.QUEUED:
        from app.mneme.infra.task_queue import enqueue_agent_run_task

        enqueue_agent_run_task(run_id=cached_record.run_id)
    return cached_record, created
