import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.config import settings
from app.mneme.crud.chat_session import create_chat_session
from app.mneme.domains.tasks.outbox import enqueue_outbox_event
from app.mneme.memoria.models.automation import HeartbeatJob
from app.mneme.memoria.persistence.automation import create_heartbeat_job, get_heartbeat_job
from app.mneme.memoria.run_models import AgentRunRecord
from app.mneme.memoria.run_submission import submit_agent_run
from app.mneme.memoria.schemas.automation import HeartbeatJobCreateRequest

BACKEND_IN_APP = "in_app"
BACKEND_INTERNAL_HOOK = "internal_hook"
EVENT_NOTIFICATION_DELIVER = "notification.deliver"
HEARTBEAT_OK = "HEARTBEAT_OK"


def heartbeat_is_active(job: HeartbeatJob, *, now: datetime | None = None) -> bool:
    local_now = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo(job.active_timezone))
    current = local_now.strftime("%H:%M")
    if job.active_start <= job.active_end:
        return job.active_start <= current < job.active_end
    return current >= job.active_start or current < job.active_end


async def create_user_heartbeat_job(
    db: AsyncSession,
    *,
    user_id: int,
    payload: HeartbeatJobCreateRequest,
) -> HeartbeatJob:
    now = datetime.now(timezone.utc)
    return await create_heartbeat_job(
        db,
        id=f"heartbeat_{uuid.uuid4().hex}",
        user_id=user_id,
        name=payload.name,
        prompt=payload.prompt,
        answer_mode=payload.answer_mode,
        knowledge_base_id=payload.knowledge_base_id,
        enabled=True,
        every_seconds=payload.every_seconds,
        active_timezone=payload.active_timezone,
        active_start=payload.active_start,
        active_end=payload.active_end,
        isolated_session=payload.isolated_session,
        light_context=payload.light_context,
        silent_success=payload.silent_success,
        event_types=payload.event_types,
        next_run_at=now,
    )


async def ensure_heartbeat_session(db: AsyncSession, job: HeartbeatJob) -> str:
    if job.session_id:
        return job.session_id
    session_id = f"heartbeat_chat_{uuid.uuid4().hex[:16]}"
    await create_chat_session(
        db,
        session_id=session_id,
        user_id=job.user_id,
        knowledge_base_id=job.knowledge_base_id,
        knowledge_base_pk=None,
        title=f"Heartbeat · {job.name}",
        answer_mode=job.answer_mode,
        system_managed=True,
    )
    job.session_id = session_id
    await db.flush()
    return session_id


async def dispatch_heartbeat_job(
    db: AsyncSession,
    *,
    job: HeartbeatJob,
    occurrence_key: str,
    force: bool = False,
) -> AgentRunRecord | None:
    if not job.enabled or (not force and not heartbeat_is_active(job)):
        job.last_status = "outside_active_hours" if job.enabled else "disabled"
        await db.flush()
        return None
    session_id = await ensure_heartbeat_session(db, job)
    record = AgentRunRecord.create(
        run_id=f"run_{uuid.uuid4().hex}",
        session_id=session_id,
        user_id=job.user_id,
        client_request_id=f"heartbeat:{job.id}:{occurrence_key}"[:128],
        question=job.prompt,
        top_k=4 if job.light_context else 8,
        answer_mode=job.answer_mode,
        trigger_type="heartbeat",
        trigger_id=job.id,
        max_attempts=settings.AGENT_RUN_MAX_ATTEMPTS,
    )
    submitted, _ = await submit_agent_run(db, record)
    job.last_run_id = submitted.run_id
    job.last_status = "queued"
    await db.flush()
    return submitted


async def finish_heartbeat_run(
    db: AsyncSession,
    *,
    record: AgentRunRecord,
    answer: str,
) -> None:
    if record.trigger_type != "heartbeat" or not record.trigger_id:
        return
    job = await get_heartbeat_job(db, job_id=record.trigger_id)
    if job is None:
        return
    job.last_status = record.status.value
    normalized = answer.strip()
    if record.status.value != "completed":
        normalized = f"Heartbeat failed: {record.error or 'unknown error'}"
    if job.silent_success and (not normalized or normalized == HEARTBEAT_OK):
        await db.flush()
        return
    await enqueue_outbox_event(
        db=db,
        event_type=EVENT_NOTIFICATION_DELIVER,
        aggregate_type="heartbeat_job",
        aggregate_id=job.id,
        target_backend=BACKEND_IN_APP,
        operation_id=record.run_id,
        payload={
            "user_id": record.user_id,
            "kind": "heartbeat",
            "title": job.name,
            "body": normalized[:8000],
            "action_url": "/?view=ai",
            "source_run_id": record.run_id,
            "metadata": {"heartbeat_job_id": job.id, "session_id": record.session_id},
        },
    )
    await db.flush()


async def emit_domain_event(
    db: AsyncSession,
    *,
    event_type: str,
    user_id: int,
    aggregate_type: str,
    aggregate_id: str,
    operation_id: str,
    payload: dict,
) -> None:
    await enqueue_outbox_event(
        db=db,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        target_backend=BACKEND_INTERNAL_HOOK,
        operation_id=operation_id,
        payload={"user_id": user_id, **payload},
    )
