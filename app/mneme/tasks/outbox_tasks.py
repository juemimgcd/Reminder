from app.mneme.conf.logging import app_logger
from app.mneme.domains.tasks.outbox import dispatch_pending_outbox_events, process_outbox_event_by_id
from app.mneme.infra.async_runner import run_task_coroutine
from app.mneme.infra.celery_app import celery_app


@celery_app.task(name="tasks.process_outbox_event_task")
def process_outbox_event_task(*, event_id: str) -> None:
    app_logger.bind(module="outbox_task").info(
        f"outbox event task start event_id={event_id}"
    )
    run_task_coroutine(process_outbox_event_by_id(event_id=event_id))


@celery_app.task(name="tasks.dispatch_pending_outbox_events_task")
def dispatch_pending_outbox_events_task(
        *,
        limit: int = 20,
        target_backend: str | None = None,
) -> None:
    app_logger.bind(module="outbox_task").info(
        f"outbox dispatch task start limit={limit} target_backend={target_backend}"
    )
    result = run_task_coroutine(
        dispatch_pending_outbox_events(
            limit=limit,
            target_backend=target_backend,
        )
    )
    app_logger.bind(module="outbox_task").info(
        f"outbox dispatch task completed matched={result['matched']} "
        f"dispatched={result['dispatched']} failed={result['failed']}"
    )
