from app.mneme.conf.config import settings
from app.mneme.conf.logging import app_logger
from app.mneme.infra.celery_app import celery_app
from app.mneme.tasks.index_tasks import index_document_task
from app.mneme.tasks.outbox_tasks import dispatch_pending_outbox_events_task, process_outbox_event_task


def enqueue_agent_run_task(*, run_id: str) -> str:
    async_result = celery_app.send_task(
        "tasks.execute_agent_run_task",
        kwargs={"run_id": run_id},
        queue=settings.CELERY_AGENT_QUEUE,
    )
    app_logger.bind(module="task_queue").info(
        f"enqueue agent run submitted run_id={run_id} celery_task_id={async_result.id}"
    )
    return async_result.id


def enqueue_maintenance_task(*, task_id: str) -> str:
    async_result = celery_app.send_task(
        "tasks.execute_maintenance_task",
        task_id=task_id,
        kwargs={"task_id": task_id},
        queue=settings.CELERY_MAINTENANCE_QUEUE,
    )
    app_logger.bind(module="task_queue").info(
        f"enqueue maintenance task submitted task_id={task_id} celery_task_id={async_result.id}"
    )
    return async_result.id


def enqueue_index_document_task(
        *,
        task_id: str,
        document_id: str,
) -> str:
    app_logger.bind(module="task_queue").info(
        f"enqueue index task start task_id={task_id} document_id={document_id} "
        f"queue={settings.CELERY_INDEX_QUEUE}"
    )

    async_result = index_document_task.apply_async(
        task_id=task_id,
        queue=settings.CELERY_INDEX_QUEUE,
        kwargs={
            "task_id": task_id,
            "document_id": document_id,
        }
    )
    app_logger.bind(module="task_queue").info(
        f"enqueue index task submitted task_id={task_id} document_id={document_id}"
    )
    return async_result.id


def cancel_index_document_task(*, task_id: str) -> None:
    app_logger.bind(module="task_queue").info(
        f"cancel index task requested task_id={task_id}"
    )
    celery_app.control.revoke(task_id)


def enqueue_process_outbox_event_task(*, event_id: str) -> str:
    app_logger.bind(module="task_queue").info(
        f"enqueue outbox event task start event_id={event_id} queue={settings.CELERY_OUTBOX_QUEUE}"
    )
    async_result = process_outbox_event_task.apply_async(
        queue=settings.CELERY_OUTBOX_QUEUE,
        kwargs={"event_id": event_id},
    )
    app_logger.bind(module="task_queue").info(
        f"enqueue outbox event task submitted event_id={event_id} celery_task_id={async_result.id}"
    )
    return async_result.id


def enqueue_dispatch_pending_outbox_events_task(
        *,
        limit: int = 20,
        target_backend: str | None = None,
) -> str:
    app_logger.bind(module="task_queue").info(
        f"enqueue outbox dispatch task start limit={limit} target_backend={target_backend} "
        f"queue={settings.CELERY_OUTBOX_QUEUE}"
    )
    async_result = dispatch_pending_outbox_events_task.apply_async(
        queue=settings.CELERY_OUTBOX_QUEUE,
        kwargs={
            "limit": limit,
            "target_backend": target_backend,
        },
    )
    app_logger.bind(module="task_queue").info(
        f"enqueue outbox dispatch task submitted celery_task_id={async_result.id}"
    )
    return async_result.id
