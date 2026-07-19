from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.memoria.models.automation import DurableAgentRun, HeartbeatJob, Notification, ToolApprovalRequest
from app.mneme.memoria.run_models import AgentRunRecord, AgentRunStatus


def durable_run_to_record(row: DurableAgentRun) -> AgentRunRecord:
    return AgentRunRecord(
        run_id=row.run_id,
        trace_id=row.trace_id,
        session_id=row.session_id,
        user_id=row.user_id,
        client_request_id=row.client_request_id,
        question=row.question,
        top_k=row.top_k,
        answer_mode=row.answer_mode,
        execution_mode=row.execution_mode,
        status=AgentRunStatus(row.status),
        trigger_type=row.trigger_type,
        trigger_id=row.trigger_id,
        attempt_count=row.attempt_count,
        max_attempts=row.max_attempts,
        created_at=row.created_at,
        started_at=row.started_at,
        completed_at=row.completed_at,
        error=row.error,
        last_event_id=row.last_event_id,
        last_event_sequence=row.last_event_sequence,
        queue_wait_ms=row.queue_wait_ms,
    )


async def create_or_get_durable_run(db: AsyncSession, record: AgentRunRecord) -> tuple[DurableAgentRun, bool]:
    statement = (
        insert(DurableAgentRun)
        .values(
            run_id=record.run_id,
            trace_id=record.trace_id,
            session_id=record.session_id,
            user_id=record.user_id,
            client_request_id=record.client_request_id,
            question=record.question,
            top_k=record.top_k,
            answer_mode=record.answer_mode,
            execution_mode=record.execution_mode,
            status=record.status.value,
            trigger_type=record.trigger_type,
            trigger_id=record.trigger_id,
            attempt_count=record.attempt_count,
            max_attempts=record.max_attempts,
            created_at=record.created_at,
        )
        .on_conflict_do_nothing(constraint="uq_agent_runs_request")
        .returning(DurableAgentRun)
    )
    created = (await db.execute(statement)).scalar_one_or_none()
    if created is not None:
        return created, True
    existing = await db.scalar(
        select(DurableAgentRun).where(
            DurableAgentRun.user_id == record.user_id,
            DurableAgentRun.session_id == record.session_id,
            DurableAgentRun.client_request_id == record.client_request_id,
        )
    )
    if existing is None:
        raise RuntimeError("durable agent run idempotency row could not be loaded")
    return existing, False


async def get_durable_run(db: AsyncSession, *, run_id: str) -> DurableAgentRun | None:
    return await db.scalar(select(DurableAgentRun).where(DurableAgentRun.run_id == run_id))


async def save_durable_run(db: AsyncSession, record: AgentRunRecord, *, touch_heartbeat: bool = False) -> None:
    row = await get_durable_run(db, run_id=record.run_id)
    if row is None:
        return
    row.status = record.status.value
    row.started_at = record.started_at
    row.completed_at = record.completed_at
    row.error = record.error
    if record.last_event_sequence >= int(row.last_event_sequence or 0):
        row.last_event_id = record.last_event_id
        row.last_event_sequence = record.last_event_sequence
    row.queue_wait_ms = record.queue_wait_ms
    row.attempt_count = record.attempt_count
    if touch_heartbeat:
        row.heartbeat_at = datetime.now(timezone.utc)
    await db.flush()


async def list_recoverable_runs(
    db: AsyncSession,
    *,
    stale_before: datetime,
    limit: int,
) -> list[DurableAgentRun]:
    result = await db.execute(
        select(DurableAgentRun)
        .where(
            DurableAgentRun.attempt_count < DurableAgentRun.max_attempts,
            or_(
                (DurableAgentRun.status == "queued") & (DurableAgentRun.updated_at < stale_before),
                (DurableAgentRun.status == "running")
                & or_(DurableAgentRun.heartbeat_at.is_(None), DurableAgentRun.heartbeat_at < stale_before),
                (DurableAgentRun.status == "aborting") & (DurableAgentRun.updated_at < stale_before),
            ),
        )
        .order_by(DurableAgentRun.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    return list(result.scalars().all())


async def list_exhausted_runs(
    db: AsyncSession,
    *,
    stale_before: datetime,
    limit: int,
) -> list[DurableAgentRun]:
    result = await db.execute(
        select(DurableAgentRun)
        .where(
            DurableAgentRun.attempt_count >= DurableAgentRun.max_attempts,
            or_(
                (DurableAgentRun.status == "queued") & (DurableAgentRun.updated_at < stale_before),
                (DurableAgentRun.status == "running")
                & or_(DurableAgentRun.heartbeat_at.is_(None), DurableAgentRun.heartbeat_at < stale_before),
                (DurableAgentRun.status == "aborting") & (DurableAgentRun.updated_at < stale_before),
            ),
        )
        .order_by(DurableAgentRun.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    return list(result.scalars().all())


async def create_heartbeat_job(db: AsyncSession, **values: Any) -> HeartbeatJob:
    job = HeartbeatJob(**values)
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job


async def get_heartbeat_job(
    db: AsyncSession,
    *,
    job_id: str,
    user_id: int | None = None,
) -> HeartbeatJob | None:
    query = select(HeartbeatJob).where(HeartbeatJob.id == job_id)
    if user_id is not None:
        query = query.where(HeartbeatJob.user_id == user_id)
    return await db.scalar(query)


async def list_heartbeat_jobs(db: AsyncSession, *, user_id: int) -> list[HeartbeatJob]:
    result = await db.execute(
        select(HeartbeatJob).where(HeartbeatJob.user_id == user_id).order_by(HeartbeatJob.created_at.desc())
    )
    return list(result.scalars().all())


async def claim_due_heartbeat_jobs(db: AsyncSession, *, now: datetime, limit: int) -> list[HeartbeatJob]:
    result = await db.execute(
        select(HeartbeatJob)
        .where(HeartbeatJob.enabled.is_(True), HeartbeatJob.next_run_at <= now)
        .order_by(HeartbeatJob.next_run_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    jobs = list(result.scalars().all())
    for job in jobs:
        job.last_run_at = now
        job.next_run_at = now + timedelta(seconds=job.every_seconds)
        job.last_status = "dispatching"
    await db.flush()
    return jobs


async def list_stuck_heartbeat_jobs(
    db: AsyncSession,
    *,
    stale_before: datetime,
    limit: int,
) -> list[HeartbeatJob]:
    result = await db.execute(
        select(HeartbeatJob)
        .where(
            HeartbeatJob.enabled.is_(True),
            HeartbeatJob.last_status == "dispatching",
            HeartbeatJob.last_run_at < stale_before,
        )
        .order_by(HeartbeatJob.last_run_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    return list(result.scalars().all())


async def list_event_heartbeat_jobs(db: AsyncSession, *, user_id: int, event_type: str) -> list[HeartbeatJob]:
    jobs = await list_heartbeat_jobs(db, user_id=user_id)
    return [job for job in jobs if job.enabled and event_type in (job.event_types or [])]


async def create_notification_if_missing(
    db: AsyncSession,
    *,
    notification_id: str,
    user_id: int,
    kind: str,
    title: str,
    body: str,
    action_url: str | None,
    source_run_id: str | None,
    idempotency_key: str,
    metadata: dict[str, Any],
) -> Notification:
    statement = (
        insert(Notification)
        .values(
            id=notification_id,
            user_id=user_id,
            kind=kind,
            title=title,
            body=body,
            action_url=action_url,
            source_run_id=source_run_id,
            idempotency_key=idempotency_key,
            metadata_json=metadata,
        )
        .on_conflict_do_nothing(constraint="uq_notifications_idempotency_key")
        .returning(Notification)
    )
    notification = (await db.execute(statement)).scalar_one_or_none()
    if notification is not None:
        return notification
    existing = await db.scalar(select(Notification).where(Notification.idempotency_key == idempotency_key))
    if existing is None:
        raise RuntimeError("notification idempotency row could not be loaded")
    return existing


async def list_notifications(db: AsyncSession, *, user_id: int, limit: int = 50) -> list[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_unread_notifications(db: AsyncSession, *, user_id: int) -> int:
    return int(
        await db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
        )
        or 0
    )


async def mark_notification_read(db: AsyncSession, *, notification_id: str, user_id: int) -> Notification | None:
    notification = await db.scalar(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
    )
    if notification is None:
        return None
    notification.read_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(notification)
    return notification


async def create_or_get_tool_approval(db: AsyncSession, **values: Any) -> ToolApprovalRequest:
    statement = (
        insert(ToolApprovalRequest)
        .values(**values)
        .on_conflict_do_nothing(constraint="uq_tool_approvals_idempotency_key")
        .returning(ToolApprovalRequest)
    )
    approval = (await db.execute(statement)).scalar_one_or_none()
    if approval is not None:
        return approval
    existing = await db.scalar(
        select(ToolApprovalRequest).where(ToolApprovalRequest.idempotency_key == values["idempotency_key"])
    )
    if existing is None:
        raise RuntimeError("tool approval idempotency row could not be loaded")
    return existing


async def get_tool_approval(
    db: AsyncSession,
    *,
    approval_id: str,
    user_id: int,
) -> ToolApprovalRequest | None:
    return await db.scalar(
        select(ToolApprovalRequest).where(
            ToolApprovalRequest.id == approval_id,
            ToolApprovalRequest.user_id == user_id,
        )
    )


async def list_tool_approvals(db: AsyncSession, *, user_id: int) -> list[ToolApprovalRequest]:
    result = await db.execute(
        select(ToolApprovalRequest)
        .where(ToolApprovalRequest.user_id == user_id)
        .order_by(ToolApprovalRequest.created_at.desc())
    )
    return list(result.scalars().all())
