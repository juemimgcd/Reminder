import asyncio
from datetime import datetime, timedelta, timezone

from app.mneme.conf.config import settings
from app.mneme.conf.database import open_write_session
from app.mneme.conf.logging import app_logger
from app.mneme.infra.celery_app import celery_app
from app.mneme.memoria.automation.service import dispatch_heartbeat_job
from app.mneme.memoria.persistence.automation import (
    claim_due_heartbeat_jobs,
    get_heartbeat_job,
    list_stuck_heartbeat_jobs,
)


@celery_app.task(name="tasks.dispatch_due_heartbeat_jobs_task")
def dispatch_due_heartbeat_jobs_task() -> None:
    count = asyncio.run(dispatch_due_heartbeat_jobs())
    app_logger.bind(module="heartbeat_scheduler").info(f"heartbeat dispatch complete count={count}")


async def dispatch_due_heartbeat_jobs() -> int:
    now = datetime.now(timezone.utc)
    async with open_write_session() as db:
        stuck = await list_stuck_heartbeat_jobs(
            db,
            stale_before=now - timedelta(seconds=settings.AGENT_RUN_STALE_SECONDS),
            limit=settings.HEARTBEAT_DISPATCH_BATCH_SIZE,
        )
        claimed = await claim_due_heartbeat_jobs(
            db,
            now=now,
            limit=settings.HEARTBEAT_DISPATCH_BATCH_SIZE,
        )
        job_ids = list(dict.fromkeys([job.id for job in stuck] + [job.id for job in claimed]))
    dispatched = 0
    for job_id in job_ids:
        async with open_write_session() as db:
            job = await get_heartbeat_job(db, job_id=job_id)
            if job is None:
                continue
            run = await dispatch_heartbeat_job(
                db,
                job=job,
                occurrence_key=f"scheduled:{int((job.last_run_at or now).timestamp())}",
            )
            dispatched += int(run is not None)
    return dispatched
