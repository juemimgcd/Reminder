import asyncio
from datetime import datetime, timedelta, timezone

from app.mneme.agent.events import AgentEvent
from app.mneme.agent.run_service import execute_agent_run
from app.mneme.conf.config import settings
from app.mneme.conf.database import open_write_session
from app.mneme.conf.logging import app_logger
from app.mneme.crud.agent_automation import (
    durable_run_to_record,
    list_exhausted_runs,
    list_recoverable_runs,
)
from app.mneme.domains.automation.service import emit_domain_event
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
        exhausted_rows = await list_exhausted_runs(
            db,
            stale_before=stale_before,
            limit=settings.AGENT_RUN_RECOVERY_BATCH_SIZE,
        )
        exhausted_records = []
        for row in exhausted_rows:
            abort_requested = row.status == "aborting"
            row.status = "aborted" if abort_requested else "failed"
            row.error = None if abort_requested else "agent run attempts exhausted"
            row.completed_at = datetime.now(timezone.utc)
            row.updated_at = row.completed_at
            exhausted_records.append(durable_run_to_record(row))
            if not abort_requested:
                await emit_domain_event(
                    db,
                    event_type="agent.run.failed",
                    user_id=row.user_id,
                    aggregate_type="agent_run",
                    aggregate_id=row.run_id,
                    operation_id=row.run_id,
                    payload={
                        "run_id": row.run_id,
                        "session_id": row.session_id,
                        "error_code": "AGENT_RUN_ATTEMPTS_EXHAUSTED",
                        "trigger_type": row.trigger_type,
                        "trigger_id": row.trigger_id,
                    },
                )
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
    for record in exhausted_records:
        cached = await agent_run_store.get(record.run_id)
        if cached is not None:
            cached.status = record.status
            cached.error = record.error
            cached.completed_at = record.completed_at
            cached.attempt_count = record.attempt_count
            await agent_run_store.save(cached)
            if record.status == "aborted":
                await agent_run_store.append_event(
                    record.run_id,
                    AgentEvent.lifecycle("aborted", loop_reason="recovered_abort_intent"),
                )
            else:
                await agent_run_store.append_event(
                    record.run_id,
                    AgentEvent.error_event(
                        "Agent run attempts exhausted.",
                        error_type="AgentRunAttemptsExhausted",
                        loop_reason="recovery_attempts_exhausted",
                    ),
                )
                await agent_run_store.append_event(
                    record.run_id,
                    AgentEvent.lifecycle("error", loop_reason="recovery_attempts_exhausted"),
                )
        await agent_run_store.remove_from_session_queue(
            session_id=record.session_id,
            run_id=record.run_id,
        )
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
    return len(records) + len(exhausted_records)
