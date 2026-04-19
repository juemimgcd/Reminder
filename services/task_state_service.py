from sqlalchemy.ext.asyncio import AsyncSession
from conf.logging import app_logger
from utils.exceptions import BusinessException
from crud.task_record import get_task_record_by_id, update_task_record_status
from models import task_record

# 定义任务状态机允许的状态迁移关系。
# 结构示例：
# {
#     "queued": ["parsing", "failed"],
#     "parsing": ["chunking", "failed"],
#     "chunking": ["embedding", "failed"],
#     "embedding": ["vector_upserting", "failed"],
#     "vector_upserting": ["completed", "failed"],
#     "failed": "queued",
# }
ALLOWED_TASK_TRANSITIONS = {
    "queued": ["parsing", "failed", "canceled"],
    "parsing": ["chunking", "failed"],
    "chunking": ["embedding", "failed"],
    "embedding": ["vector_upserting", "failed"],
    "vector_upserting": ["completed", "failed"],
    "failed": ["queued"],
    "canceled": ["queued"],

}


# 按状态机规则推动 task_record 的状态迁移，并在需要时写入错误信息。
async def transition_task_status(
        db: AsyncSession,
        *,
        task_id: str,
        to_status: str,
        error_message: str | None = None,
):
    # 你要做的事：
    # 1. 查询 task_record
    # 2. 读取当前状态
    # 3. 判断 current -> to_status 是否合法
    # 4. 同状态直接返回
    # 5. 非法迁移抛异常
    # 6. 合法迁移则更新 task_record.status
    task_recd = await get_task_record_by_id(db, task_id=task_id)
    if task_recd:
        apparent_status = task_recd.status
        if apparent_status == to_status:
            app_logger.bind(module="task_state").info(
                f"task status unchanged task_id={task_id} status={to_status}"
            )
            return task_recd
        if to_status in ALLOWED_TASK_TRANSITIONS.get(apparent_status, []):
            app_logger.bind(module="task_state").info(
                f"task status transition task_id={task_id} from_status={apparent_status} to_status={to_status}"
            )
            task_recd.status = to_status
        else:
            app_logger.bind(module="task_state").warning(
                f"task status illegal transition task_id={task_id} "
                f"from_status={apparent_status} to_status={to_status}"
            )
            raise BusinessException(
                message=f"非法状态迁移: {apparent_status} -> {to_status}",
                code=4009,
                status_code=400,
            )
    else:
        app_logger.bind(module="task_state").warning(
            f"task status transition target missing task_id={task_id} to_status={to_status}"
        )
    return await update_task_record_status(
        db,
        task_id=task_id,
        status=to_status,
        error_message=error_message,
    )
