from sqlalchemy.ext.asyncio import AsyncSession

from crud.document import get_document_by_id, update_document_status
from crud.task_record import get_task_record_by_id
from infra.task_queue import cancel_index_document_task, enqueue_index_document_task
from models.user import User
from services.document_service import submit_document_index_task
from services.task_state_service import transition_task_status
from utils.exceptions import BusinessException


async def ensure_document_index_task_belongs_to_user(
        db: AsyncSession,
        *,
        task_id: str,
        current_user: User,
):
    task = await get_task_record_by_id(db, task_id=task_id)
    if not task:
        raise BusinessException(message="任务不存在", code=4043, status_code=404)

    if task.task_type != "document_index":
        raise BusinessException(message="当前仅支持文档索引任务", code=4018, status_code=400)

    document = await get_document_by_id(
        db,
        document_id=task.target_id,
        user_id=current_user.id,
    )
    if not document:
        raise BusinessException(message="你无权访问该任务", code=4007, status_code=403)

    return task, document


async def cancel_document_index_task(
        db: AsyncSession,
        *,
        task_id: str,
        current_user: User,
) -> dict[str, str | None]:
    task, document = await ensure_document_index_task_belongs_to_user(
        db,
        task_id=task_id,
        current_user=current_user,
    )

    if task.status != "queued":
        raise BusinessException(message="只有排队中的任务可以取消", code=4019, status_code=400)

    cancel_index_document_task(task_id=task_id)
    await transition_task_status(
        db,
        task_id=task_id,
        to_status="canceled",
    )
    await update_document_status(
        db,
        document_id=document.id,
        status="uploaded",
    )
    await db.commit()

    return {
        "task_id": task_id,
        "status": "canceled",
        "document_id": document.id,
        "message": "task canceled",
    }


async def retry_document_index_task(
        db: AsyncSession,
        *,
        task_id: str,
        current_user: User,
) -> dict[str, str | None]:
    task, document = await ensure_document_index_task_belongs_to_user(
        db,
        task_id=task_id,
        current_user=current_user,
    )

    if task.status not in {"failed", "canceled"}:
        raise BusinessException(message="只有失败或已取消的任务可以重试", code=4020, status_code=400)

    result = await submit_document_index_task(
        db,
        document_id=document.id,
    )
    await db.commit()
    enqueue_index_document_task(
        task_id=result["task_id"],
        document_id=document.id,
    )

    return {
        "task_id": result["task_id"],
        "status": result["status"],
        "document_id": document.id,
        "message": "task retried",
    }
