import hashlib
import json
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.config import settings
from app.mneme.crud.chat_session import create_chat_session
from app.mneme.domains.tasks.outbox import (
    _contains_secret,
    build_outbox_idempotency_key,
    enqueue_outbox_event,
)
from app.mneme.memoria.actions import WRITE_ACTION_CATALOG
from app.mneme.memoria.models.automation import HeartbeatJob
from app.mneme.memoria.persistence.automation import (
    create_heartbeat_job,
    create_notification_if_missing,
    create_or_get_tool_approval,
    get_heartbeat_job,
)
from app.mneme.memoria.run_models import AgentRunRecord
from app.mneme.memoria.run_submission import submit_agent_run
from app.mneme.memoria.schemas.automation import HeartbeatJobCreateRequest
from app.mneme.memoria.schemas.memory_agent import MemoryAgentEvent
from app.mneme.memoria.subscribers.contracts import RuntimeSubscriberEvent, SubscriberAction

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


async def apply_runtime_subscriber_action(
    *,
    db: AsyncSession,
    event: RuntimeSubscriberEvent,
    subscriber_name: str,
    action: SubscriberAction,
    idempotency_key: str,
) -> dict:
    payload = action.payload
    target_user_id = payload.get("user_id")
    if target_user_id is not None and target_user_id != event.user_id:
        raise ValueError("subscriber action user scope mismatch")

    if action.type == "create_approval":
        action_name = _required_action_text(payload, "action_name", max_chars=120)
        definition = WRITE_ACTION_CATALOG.get(action_name)
        if definition is None:
            raise ValueError("subscriber approval action is unsupported")
        summary = _required_action_text(payload, "summary", max_chars=2_000)
        arguments = payload.get("arguments", {})
        if not isinstance(arguments, dict) or _contains_secret(json.dumps(arguments, default=str)):
            raise ValueError("subscriber approval arguments are invalid")
        approval = await create_or_get_tool_approval(
            db,
            id=_stable_action_id("approval", idempotency_key),
            user_id=event.user_id,
            run_id=event.run_id,
            action_name=definition.name,
            risk_level=definition.risk_level.value,
            action_summary=summary,
            arguments_json=arguments,
            status="pending",
            apply_enabled=definition.apply_enabled,
            idempotency_key=idempotency_key,
        )
        return {"approval_id": approval.id, "user_id": approval.user_id}

    if action.type == "send_notification":
        title = _required_action_text(payload, "title", max_chars=255)
        body = _optional_action_text(payload, "body", max_chars=8_000)
        notification = await create_notification_if_missing(
            db,
            notification_id=_stable_action_id("notification", idempotency_key),
            user_id=event.user_id,
            kind=_optional_action_text(payload, "kind", max_chars=50) or "agent",
            title=title,
            body=body,
            action_url=_optional_action_text(payload, "action_url", max_chars=500) or None,
            source_run_id=event.run_id,
            idempotency_key=idempotency_key,
            metadata={"subscriber_name": subscriber_name},
        )
        return {"notification_id": notification.id, "user_id": notification.user_id}

    knowledge_base_id = _required_action_text(payload, "knowledge_base_id", max_chars=64)
    session_id = _required_action_text(payload, "session_id", max_chars=64)
    message_id = _required_action_text(payload, "message_id", max_chars=64)
    excerpt = _required_action_text(payload, "excerpt", max_chars=20_000)
    memory_event = MemoryAgentEvent(
        event_id=_stable_action_id("subscriber-context", idempotency_key),
        event_type="user.memory_requested",
        occurred_at=datetime.now(timezone.utc),
        owner_id=event.user_id,
        knowledge_base_id=knowledge_base_id,
        payload={
            "session_id": session_id,
            "message_id": message_id,
            "message_created_at": datetime.now(timezone.utc).isoformat(),
            "excerpt": excerpt,
            "subscriber_name": subscriber_name,
        },
    )
    operation_id = idempotency_key
    if len(
        build_outbox_idempotency_key(
            event_type=memory_event.event_type,
            aggregate_type="subscriber_action",
            aggregate_id=memory_event.event_id,
            operation_id=operation_id,
        )
    ) > 200:
        operation_id = _stable_action_id("subscriber-action", idempotency_key)
    outbox_event = await enqueue_outbox_event(
        db=db,
        event_type=memory_event.event_type,
        aggregate_type="subscriber_action",
        aggregate_id=memory_event.event_id,
        target_backend=settings.MEMORY_AGENT_OUTBOX_TARGET,
        operation_id=operation_id,
        payload=memory_event.model_dump(mode="json"),
    )
    return {"outbox_event_id": outbox_event.id, "user_id": event.user_id}


def _stable_action_id(prefix: str, idempotency_key: str) -> str:
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    return f"{prefix}_{digest}"[:64]


def _required_action_text(payload: dict, key: str, *, max_chars: int) -> str:
    value = _optional_action_text(payload, key, max_chars=max_chars)
    if not value:
        raise ValueError(f"subscriber action missing {key}")
    return value


def _optional_action_text(payload: dict, key: str, *, max_chars: int) -> str:
    value = payload.get(key)
    if value is None:
        return ""
    if not isinstance(value, str) or _contains_secret(value):
        raise ValueError(f"subscriber action has invalid {key}")
    return value.strip()[:max_chars]
