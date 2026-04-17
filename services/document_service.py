import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from crud import task_record
from crud.document import get_document_by_id, update_document_status
from crud.task_record import create_task_record
from models.document import Document
from utils.exceptions import BusinessException


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
        raise BusinessException(message="document not found",code=404)

    if doc.status == "indexing":
        raise BusinessException(message="document is indexing")

    if doc.status == "indexed":
        raise BusinessException(message="document has already indexed")

    return doc



def build_index_task_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"task_index_{timestamp}_{uuid.uuid4().hex[:6]}"






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
    # 5. 投递任务
    # 6. 返回任务提交结果
    doc = await get_document_by_id(db,document_id=document_id)
    if not doc:
        raise BusinessException(message="document not found",code=404)

    task_id = build_index_task_id()
    await create_task_record(
        db,
        task_id=task_id,
        task_type="document_index",
        status="queued",
        target_id=doc.id

    )

    await update_document_status(db,document_id=doc.id,status="queued")
    await ensure_document_can_index(db,document_id=doc.id)

    return {
        "task_id": task_id,
        "document_id": doc.id,
        "knowledge_base_id": doc.knowledge_base_id,
        "status": "queued",
        "message": "index task submitted",
    }





















