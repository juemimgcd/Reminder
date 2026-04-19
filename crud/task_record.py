from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.task_record import TaskRecord


# 创建一条新的任务记录并写入当前 session。
async def create_task_record(
        db: AsyncSession,
        *,
        task_id: str,
        task_type: str,
        target_id: str,
        status: str = "queued",
) -> TaskRecord:
    # 你要做的事：
    # 1. 构造 TaskRecord
    # 2. add 到 session
    # 3. flush
    # 4. refresh
    # 5. 返回 task
    task_record = TaskRecord(
        id=task_id,
        task_type=task_type,
        target_id=target_id,
        status=status

    )
    db.add(task_record)
    await db.flush()
    await db.refresh(task_record)

    return task_record



# 按 task_id 查询单条任务记录。
async def get_task_record_by_id(
        db: AsyncSession,
        *,
        task_id: str,
) -> TaskRecord | None:
    result = await db.execute(
        select(TaskRecord).where(TaskRecord.id == task_id)
    )
    return result.scalar_one_or_none()




# 更新任务记录状态，并在需要时补充错误信息。
async def update_task_record_status(
        db: AsyncSession,
        *,
        task_id: str,
        status: str,
        error_message: str | None = None,
) -> TaskRecord | None:
    result = await db.execute(
        select(TaskRecord).where(TaskRecord.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        return None

    task.status = status
    if error_message is not None:
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








