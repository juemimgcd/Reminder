from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.config import settings
from app.mneme.crud.document import get_document_by_id, update_document_status
from app.mneme.crud.task_record import get_task_record_by_id
from app.mneme.infra.rate_limit import enforce_fixed_window_rate_limit
from app.mneme.infra.task_queue import cancel_index_document_task, enqueue_index_document_task
from app.mneme.models.user import User
from app.mneme.domains.graph.projection import sync_document_projection_from_db
from app.mneme.domains.tasks.state import CANCELLED, FAILED, PENDING, RETRYING, transition_task_status
from app.mneme.utils.exceptions import BusinessException


async def ensure_document_index_task_belongs_to_user(
        db: AsyncSession,
        *,
        task_id: str,
        current_user: User,
):
    task = await get_task_record_by_id(db, task_id=task_id)
    if not task:
        raise BusinessException(message="task not found", code=4043, status_code=404)

    if task.task_type != "document_index":
        raise BusinessException(message="only document_index tasks can be managed here", code=4018, status_code=400)

    document = await get_document_by_id(
        db,
        document_id=task.target_id,
        user_id=current_user.id,
    )
    if not document:
        raise BusinessException(message="you do not have access to this task", code=4007, status_code=403)

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

    if task.status not in {PENDING, "queued"}:
        raise BusinessException(message="only queued tasks can be canceled", code=4019, status_code=400)

    cancel_index_document_task(task_id=task_id)
    await transition_task_status(
        db,
        task_id=task_id,
        to_status=CANCELLED,
    )
    await update_document_status(
        db,
        document_id=document.id,
        status="uploaded",
    )
    await db.commit()

    return {
        "task_id": task_id,
        "status": CANCELLED,
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

    if task.status not in {FAILED, CANCELLED, "failed", "canceled"}:
        raise BusinessException(message="only failed or cancelled tasks can be retried", code=4020, status_code=400)

    await transition_task_status(
        db,
        task_id=task_id,
        to_status=RETRYING,
    )
    enforce_fixed_window_rate_limit(
        bucket="index_submit",
        key=f"user:{document.user_id}:kb:{document.knowledge_base_id}",
        limit=settings.INDEX_SUBMIT_RATE_LIMIT_MAX,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )
    await transition_task_status(
        db,
        task_id=task_id,
        to_status=PENDING,
        result_summary="retry queued",
    )
    queued_document = await update_document_status(
        db,
        document_id=document.id,
        status="queued",
    )
    if queued_document:
        await sync_document_projection_from_db(
            db,
            document=queued_document,
        )
    await db.commit()
    enqueue_index_document_task(
        task_id=task_id,
        document_id=document.id,
    )

    return {
        "task_id": task_id,
        "status": PENDING,
        "document_id": document.id,
        "message": "task retried",
    }
