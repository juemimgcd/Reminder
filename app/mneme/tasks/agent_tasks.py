import asyncio
from datetime import datetime, timedelta, timezone

from app.mneme.agent.run_service import execute_agent_run
from app.mneme.conf.config import settings
from app.mneme.conf.database import open_write_session
from app.mneme.conf.logging import app_logger
from app.mneme.crud.agent_automation import durable_run_to_record, list_recoverable_runs
from app.mneme.infra.agent_runs import agent_run_store
from app.mneme.infra.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="tasks.execute_agent_run_task",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=settings.CELERY_TASK_MAX_RETRIES,
)
def execute_agent_run_task(self, *, run_id: str) -> None:
    app_logger.bind(module="agent_worker").info(f"agent run task start run_id={run_id}")
    asyncio.run(execute_agent_run(run_id))


@celery_app.task(name="tasks.recover_agent_runs_task")
def recover_agent_runs_task() -> None:
    asyncio.run(recover_agent_runs())


async def recover_agent_runs() -> int:
    stale_before = datetime.now(timezone.utc) - timedelta(seconds=settings.AGENT_RUN_STALE_SECONDS)
    async with open_write_session() as db:
        rows = await list_recoverable_runs(
            db,
            stale_before=stale_before,
            limit=settings.AGENT_RUN_RECOVERY_BATCH_SIZE,
        )
        records = []
        for row in rows:
            if row.status != "aborting":
                row.status = "queued"
                row.started_at = None
                row.heartbeat_at = None
            # Claim the recovery window in PostgreSQL before publishing.  In
            # particular, an already-queued row otherwise receives no dirty
            # field and remains eligible for every recovery scan.
            row.updated_at = datetime.now(timezone.utc)
            records.append(durable_run_to_record(row))
    for record in records:
        cached = await agent_run_store.get(record.run_id)
        if cached is None:
            await agent_run_store.create_or_get_and_enqueue(record)
        else:
            cached.status = record.status
            cached.started_at = None
            cached.attempt_count = record.attempt_count
            await agent_run_store.save(cached)
        execute_agent_run_task.apply_async(
            kwargs={"run_id": record.run_id},
            queue=settings.CELERY_AGENT_QUEUE,
        )
    return len(records)
