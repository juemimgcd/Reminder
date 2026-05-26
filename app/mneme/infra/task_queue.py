from app.mneme.conf.logging import app_logger
from app.mneme.infra.celery_app import celery_app
from app.mneme.tasks.index_tasks import index_document_task
from app.mneme.tasks.outbox_tasks import dispatch_pending_outbox_events_task, process_outbox_event_task
from app.mneme.conf.config import settings


def enqueue_index_document_task(
        *,
        task_id: str,
        document_id: str,
) -> str:
    # 浣犺鍋氱殑浜嬶細
    # 1. 璋冪敤 tasks.index_tasks.index_document_task
    # 2. 鎶?task_id 鍜?document_id 浼犺繘鍘?
    # 3. Day 3 鍙互鍏堝仛鍗犱綅锛孌ay 4 鍐嶆帴 Celery
    app_logger.bind(module="task_queue").info(
        f"enqueue index task start task_id={task_id} document_id={document_id} "
        f"queue={settings.CELERY_INDEX_QUEUE}"
    )

    # 浣犺鍋氱殑浜嬶細
    # 1. 瀵煎叆 Celery task
    # 2. 璋冪敤 delay 鎴?apply_async
    # 3. 浼犲叆 task_id 鍜?document_id
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
