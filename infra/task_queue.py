from conf.logging import app_logger
from infra.celery_app import celery_app
from tasks.index_tasks import index_document_task


def enqueue_index_document_task(
        *,
        task_id: str,
        document_id: str,
) -> None:
    # 你要做的事：
    # 1. 调用 tasks.index_tasks.index_document_task
    # 2. 把 task_id 和 document_id 传进去
    # 3. Day 3 可以先做占位，Day 4 再接 Celery
    app_logger.bind(moduel="task_queue").info(
        "index task queued",
        task_id=task_id,
        document_id=document_id
    )

    # 你要做的事：
    # 1. 导入 Celery task
    # 2. 调用 delay 或 apply_async
    # 3. 传入 task_id 和 document_id
    index_document_task.apply_async(
        kwargs={
            "task_id": task_id,
            "document_id": document_id,
        }
    )