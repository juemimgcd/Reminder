import uuid

from app.mneme.conf.database import open_write_session
from app.mneme.memoria.automation.service import (
    apply_runtime_subscriber_action,
    dispatch_heartbeat_job,
)
from app.mneme.memoria.persistence.automation import (
    create_notification_if_missing,
    get_heartbeat_job,
    list_event_heartbeat_jobs,
)
from app.mneme.memoria.subscribers.contracts import RuntimeSubscriberEvent
from app.mneme.memoria.subscribers.dispatcher import dispatch_runtime_subscribers
from app.mneme.memoria.subscribers.registry import runtime_subscriber_registry
from app.mneme.models.outbox_event import OutboxEvent
from app.mneme.utils.exceptions import BusinessException


async def apply_in_app_notification_event(event: OutboxEvent) -> dict:
    payload = event.payload
    user_id = payload.get("user_id")
    if not isinstance(user_id, int):
        raise BusinessException(message="notification event missing user_id", code=5021, status_code=500)
    async with open_write_session() as db:
        notification = await create_notification_if_missing(
            db,
            notification_id=f"notification_{uuid.uuid4().hex}",
            user_id=user_id,
            kind=str(payload.get("kind") or "agent"),
            title=str(payload.get("title") or "Agent notification")[:255],
            body=str(payload.get("body") or ""),
            action_url=payload.get("action_url"),
            source_run_id=payload.get("source_run_id"),
            idempotency_key=event.idempotency_key,
            metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
        )
        return {"notification_id": notification.id, "user_id": notification.user_id}


async def apply_internal_hook_event(event: OutboxEvent) -> dict:
    user_id = event.payload.get("user_id")
    if not isinstance(user_id, int):
        raise BusinessException(message="hook event missing user_id", code=5022, status_code=500)
    dispatched: list[str] = []
    async with open_write_session() as db:
        subscriber_event = RuntimeSubscriberEvent(
            event_id=event.id,
            event_type=event.event_type,
            user_id=user_id,
            run_id=_optional_string(event.payload.get("run_id") or event.payload.get("source_run_id")),
            idempotency_key=event.idempotency_key,
            payload=event.payload,
        )

        async def apply_action(**kwargs):
            return await apply_runtime_subscriber_action(db=db, **kwargs)

        subscriber_results = await dispatch_runtime_subscribers(
            subscriber_event,
            registry=runtime_subscriber_registry,
            apply_action=apply_action,
        )
        jobs = await list_event_heartbeat_jobs(db, user_id=user_id, event_type=event.event_type)
        for job in jobs:
            if event.payload.get("trigger_type") == "heartbeat" and event.payload.get("trigger_id") == job.id:
                continue
            current = await get_heartbeat_job(db, job_id=job.id)
            if current is None:
                continue
            run = await dispatch_heartbeat_job(
                db,
                job=current,
                occurrence_key=f"event:{event.id}",
            )
            if run is not None:
                dispatched.append(run.run_id)
    return {
        "event_type": event.event_type,
        "dispatched_run_ids": dispatched,
        "subscriber_results": [result.model_dump(mode="json") for result in subscriber_results],
    }


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None
