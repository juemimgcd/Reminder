from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.database import get_database, get_write_database
from app.mneme.crud.document import get_document_by_id
from app.mneme.crud.task_record import get_task_record_by_id
from app.mneme.models.user import User
from app.mneme.schemas.task_record import TaskActionData, TaskRecordData
from app.mneme.services.task_admin_service import cancel_document_index_task, retry_document_index_task
from app.mneme.utils.auth import get_current_user
from app.mneme.utils.exceptions import BusinessException
from app.mneme.utils.response import success_response


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}")
async def get_task_status(
        task_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    task = await get_task_record_by_id(db, task_id=task_id)
    if not task:
        raise BusinessException(message="task not found", code=4043, status_code=404)

    if task.task_type == "document_index":
        document = await get_document_by_id(
            db,
            document_id=task.target_id,
            user_id=current_user.id,
        )
        if not document:
            raise BusinessException(message="浣犳棤鏉冩煡鐪嬭浠诲姟", code=4007, status_code=403)

    data = TaskRecordData.model_validate(task)
    return success_response(data=data)


@router.post("/{task_id}/cancel")
async def cancel_task(
        task_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_write_database),
):
    result = await cancel_document_index_task(
        db,
        task_id=task_id,
        current_user=current_user,
    )
    return success_response(
        data=TaskActionData(**result),
        message="task canceled",
    )


@router.post("/{task_id}/retry")
async def retry_task(
        task_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_write_database),
):
    result = await retry_document_index_task(
        db,
        task_id=task_id,
        current_user=current_user,
    )
    return success_response(
        data=TaskActionData(**result),
        message="task retried",
    )
