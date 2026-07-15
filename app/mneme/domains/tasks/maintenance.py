import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.config import settings
from app.mneme.conf.logging import app_logger
from app.mneme.crud.task_record import create_task_record
from app.mneme.infra.task_queue import enqueue_maintenance_task
from app.mneme.models.task_record import TaskRecord

GRAPH_REBUILD_USER = "graph_rebuild_user"
GRAPH_REBUILD_KNOWLEDGE_BASE = "graph_rebuild_knowledge_base"
MEMORY_REBUILD_KNOWLEDGE_BASE = "memory_rebuild_knowledge_base"
MAINTENANCE_TASK_TYPES = {
    GRAPH_REBUILD_USER,
    GRAPH_REBUILD_KNOWLEDGE_BASE,
    MEMORY_REBUILD_KNOWLEDGE_BASE,
}


async def submit_maintenance_task(
    db: AsyncSession,
    *,
    task_type: str,
    target_id: str,
) -> TaskRecord:
    if task_type not in MAINTENANCE_TASK_TYPES:
        raise ValueError(f"unsupported maintenance task type: {task_type}")
    task_id = f"task_{uuid.uuid4().hex}"
    task = await create_task_record(
        db,
        task_id=task_id,
        task_type=task_type,
        target_id=target_id,
        status="pending",
        progress_stage="queued",
        queue_name=settings.CELERY_MAINTENANCE_QUEUE,
        celery_task_id=task_id,
        max_attempts=settings.CELERY_TASK_MAX_RETRIES,
    )
    await db.commit()
    try:
        enqueue_maintenance_task(task_id=task_id)
    except Exception as exc:
        app_logger.bind(module="maintenance_submit").warning(
            f"maintenance publish deferred to recovery task_id={task_id} error_type={type(exc).__name__}"
        )
    return task
