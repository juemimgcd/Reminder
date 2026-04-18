import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from conf.config import settings
from conf.logging import app_logger
from crud.document import get_document_by_id, update_document_status
from crud.task_record import create_task_record
from infra.rate_limit import enforce_fixed_window_rate_limit
from models.document import Document
from utils.exceptions import BusinessException


# 校验文档是否存在，以及当前状态是否允许再次进入索引。
async def ensure_document_can_index(
        db: AsyncSession,
        *,
        document_id: str,
) -> Document:
    # 你要做的事：
    # 1. 读 document
    # 2. 判断是否存在
    # 3. 判断当前状态是否允许进入索引
    # 4. 返回 document
    doc = await get_document_by_id(db,document_id=document_id)
    if not doc:
        app_logger.bind(module="document_service").warning(
            f"index check failed document_id={document_id} reason=document_not_found"
        )
        raise BusinessException(message="document not found",code=404)

    if doc.status == "indexing":
        app_logger.bind(module="document_service").warning(
            f"index check failed document_id={document_id} status={doc.status}"
        )
        raise BusinessException(message="document is indexing")

    if doc.status == "indexed":
        app_logger.bind(module="document_service").warning(
            f"index check failed document_id={document_id} status={doc.status}"
        )
        raise BusinessException(message="document has already indexed")

    return doc



# 生成文档索引任务使用的 task_id。
def build_index_task_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"task_index_{timestamp}_{uuid.uuid4().hex[:6]}"






# 提交文档索引任务，并在入队前完成限流和状态校验。
async def submit_document_index_task(
        db: AsyncSession,
        *,
        document_id: str,
) -> dict:
    # 你要做的事：
    # 1. 校验 document 是否存在、是否可索引
    # 2. 生成 task_id
    # 3. 创建 task_record
    # 4. 更新 document.status 为 queued
    # 5. 由调用方在 commit 后投递任务
    # 6. 返回任务提交结果
    doc = await ensure_document_can_index(
        db,
        document_id=document_id,
    )
    app_logger.bind(module="document_service").info(
        f"submit index task start document_id={doc.id} user_id={doc.user_id} "
        f"knowledge_base_id={doc.knowledge_base_id} status={doc.status}"
    )

    # 这里的限流 key 形如 "user:1:kb:kb_demo_001"，用于限制重复索引提交。
    enforce_fixed_window_rate_limit(
        bucket="index_submit",
        key=f"user:{doc.user_id}:kb:{doc.knowledge_base_id}",
        limit=settings.INDEX_SUBMIT_RATE_LIMIT_MAX,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )


    task_id = build_index_task_id()
    await create_task_record(
        db,
        task_id=task_id,
        task_type="document_index",
        status="queued",
        target_id=doc.id

    )

    await update_document_status(db, document_id=doc.id, status="queued")
    app_logger.bind(module="document_service").info(
        f"submit index task prepared task_id={task_id} document_id={doc.id} "
        f"knowledge_base_id={doc.knowledge_base_id}"
    )

    return {
        "task_id": task_id,
        "document_id": doc.id,
        "knowledge_base_id": doc.knowledge_base_id,
        "status": "queued",
        "message": "index task submitted",
    }





















