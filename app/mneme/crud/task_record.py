from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.models.task_record import TaskRecord


async def create_task_record(
        db: AsyncSession,
        *,
        task_id: str,
        task_type: str,
        target_id: str,
        status: str = "pending",
        progress_stage: str | None = None,
        queue_name: str | None = None,
        celery_task_id: str | None = None,
        attempt_count: int = 0,
        max_attempts: int = 3,
) -> TaskRecord:
    # 3. flush
    # 4. refresh
    task_record = TaskRecord(
        id=task_id,
        task_type=task_type,
        target_id=target_id,
        status=status,
        progress_stage=progress_stage,
        queue_name=queue_name,
        celery_task_id=celery_task_id,
        attempt_count=attempt_count,
        max_attempts=max_attempts,

    )
    db.add(task_record)
    await db.flush()
    await db.refresh(task_record)

    return task_record



async def get_task_record_by_id(
        db: AsyncSession,
        *,
        task_id: str,
) -> TaskRecord | None:
    result = await db.execute(
        select(TaskRecord).where(TaskRecord.id == task_id)
    )
    return result.scalar_one_or_none()




async def update_task_record_status(
        db: AsyncSession,
        *,
        task_id: str,
        status: str,
        progress_stage: str | None = None,
        clear_progress_stage: bool = False,
        increment_attempt: bool = False,
        result_summary: str | None = None,
        error_message: str | None = None,
        clear_error: bool = False,
) -> TaskRecord | None:
    result = await db.execute(
        select(TaskRecord).where(TaskRecord.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        return None

    task.status = status
    if clear_progress_stage:
        task.progress_stage = None
    elif progress_stage is not None:
        task.progress_stage = progress_stage
    if increment_attempt:
        task.attempt_count += 1
    if result_summary is not None:
        task.result_summary = result_summary
    if clear_error:
        task.error_message = None
    elif error_message is not None:
        task.error_message = error_message

    await db.flush()
    await db.refresh(task)
    return task


async def list_task_records_by_target_id(
        db: AsyncSession,
        *,
        target_id: str,
        task_type: str | None = None,
) -> list[TaskRecord]:
    sql = select(TaskRecord).where(TaskRecord.target_id == target_id)
    if task_type:
        sql = sql.where(TaskRecord.task_type == task_type)
    sql = sql.order_by(TaskRecord.created_at.desc())
    result = await db.execute(sql)
    return list(result.scalars().all())


async def get_latest_task_record_by_target_id(
        db: AsyncSession,
        *,
        target_id: str,
        task_type: str | None = None,
) -> TaskRecord | None:
    rows = await list_task_records_by_target_id(
        db,
        target_id=target_id,
        task_type=task_type,
    )
    return rows[0] if rows else None


async def delete_task_records_by_target_id(
        db: AsyncSession,
        *,
        target_id: str,
        task_type: str | None = None,
) -> int:
    sql = delete(TaskRecord).where(TaskRecord.target_id == target_id)
    if task_type:
        sql = sql.where(TaskRecord.task_type == task_type)
    result = await db.execute(sql)
    return result.rowcount or 0








