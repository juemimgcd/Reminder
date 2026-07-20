import json
from datetime import datetime, timedelta, timezone

from app.mneme.conf.config import settings
from app.mneme.conf.database import open_read_session, open_write_session
from app.mneme.conf.logging import app_logger
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id
from app.mneme.crud.task_record import (
    claim_maintenance_task,
    list_recoverable_maintenance_tasks,
)
from app.mneme.crud.user import get_user_by_id
from app.mneme.domains.graph.admin import (
    rebuild_graph_projection_for_knowledge_base,
    rebuild_graph_projection_for_user,
)
from app.mneme.domains.memory.service import rebuild_memory_entries_for_knowledge_base
from app.mneme.domains.tasks.maintenance import (
    GRAPH_REBUILD_KNOWLEDGE_BASE,
    GRAPH_REBUILD_USER,
    MEMORY_REBUILD_KNOWLEDGE_BASE,
)
from app.mneme.domains.tasks.state import FAILED, SUCCEEDED, transition_task_status
from app.mneme.infra.async_runner import run_task_coroutine
from app.mneme.infra.celery_app import celery_app
from app.mneme.infra.task_queue import enqueue_maintenance_task


@celery_app.task(name="tasks.execute_maintenance_task")
def execute_maintenance_task(*, task_id: str) -> None:
    run_task_coroutine(run_maintenance_task(task_id))


@celery_app.task(name="tasks.recover_maintenance_tasks")
def recover_maintenance_tasks() -> None:
    run_task_coroutine(recover_stale_maintenance_tasks())


async def run_maintenance_task(task_id: str) -> None:
    async with open_write_session() as db:
        task = await claim_maintenance_task(db, task_id=task_id)
        if task is None:
            return
        task_type = task.task_type
        target_id = task.target_id
    try:
        if task_type == MEMORY_REBUILD_KNOWLEDGE_BASE:
            async with open_read_session() as db:
                knowledge_base = await get_knowledge_base_by_id(db, target_id)
                if knowledge_base is None:
                    raise RuntimeError("maintenance task knowledge base no longer exists")
                knowledge_base_pk = knowledge_base.pk
                knowledge_base_id = knowledge_base.id
            result = await rebuild_memory_entries_for_knowledge_base(
                knowledge_base_pk=knowledge_base_pk,
                knowledge_base_id=knowledge_base_id,
            )
        else:
            async with open_read_session() as db:
                if task_type == GRAPH_REBUILD_USER:
                    user = await get_user_by_id(db, user_id=int(target_id))
                    if user is None:
                        raise RuntimeError("maintenance task user no longer exists")
                    result = await rebuild_graph_projection_for_user(db, current_user=user)
                elif task_type == GRAPH_REBUILD_KNOWLEDGE_BASE:
                    knowledge_base = await get_knowledge_base_by_id(db, target_id)
                    if knowledge_base is None:
                        raise RuntimeError("maintenance task knowledge base no longer exists")
                    user = await get_user_by_id(db, user_id=knowledge_base.user_id)
                    if user is None:
                        raise RuntimeError("maintenance task user no longer exists")
                    result = await rebuild_graph_projection_for_knowledge_base(
                        db,
                        current_user=user,
                        knowledge_base_id=target_id,
                    )
                else:
                    raise RuntimeError(f"unsupported maintenance task type: {task_type}")
        async with open_write_session() as db:
            await transition_task_status(
                db,
                task_id=task_id,
                to_status=SUCCEEDED,
                result_summary=json.dumps(result, ensure_ascii=False, default=str),
            )
    except Exception as exc:
        app_logger.bind(module="maintenance_worker").exception(
            f"maintenance task failed task_id={task_id} task_type={task_type} error={exc}"
        )
        async with open_write_session() as db:
            await transition_task_status(db, task_id=task_id, to_status=FAILED, error_message=str(exc))
        raise


async def recover_stale_maintenance_tasks() -> int:
    now = datetime.now(timezone.utc)
    async with open_write_session() as db:
        rows = await list_recoverable_maintenance_tasks(
            db,
            pending_before=now - timedelta(seconds=settings.MAINTENANCE_PENDING_RECOVERY_SECONDS),
            running_before=now - timedelta(seconds=settings.MAINTENANCE_TASK_STALE_SECONDS),
            limit=settings.MAINTENANCE_RECOVERY_BATCH_SIZE,
        )
        task_ids = [row.id for row in rows if row.status == "pending"]
    for task_id in task_ids:
        enqueue_maintenance_task(task_id=task_id)
    return len(task_ids)
