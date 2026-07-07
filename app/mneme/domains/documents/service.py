import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.config import settings
from app.mneme.conf.logging import app_logger
from app.mneme.crud.document import get_document_by_id, update_document_status
from app.mneme.crud.task_record import create_task_record
from app.mneme.infra.rate_limit import enforce_fixed_window_rate_limit
from app.mneme.models.document import Document
from app.mneme.domains.graph.projection import sync_document_projection_from_db
from app.mneme.utils.exceptions import BusinessException


async def ensure_document_can_index(
        db: AsyncSession,
        *,
        document_id: str,
) -> Document:
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



def build_index_task_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"task_index_{timestamp}_{uuid.uuid4().hex[:6]}"






async def submit_document_index_task(
        db: AsyncSession,
        *,
        document_id: str,
) -> dict:
    doc = await ensure_document_can_index(
        db,
        document_id=document_id,
    )
    app_logger.bind(module="document_service").info(
        f"submit index task start document_id={doc.id} user_id={doc.user_id} "
        f"knowledge_base_id={doc.knowledge_base_id} status={doc.status}"
    )

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
        status="pending",
        queue_name=settings.CELERY_INDEX_QUEUE,
        celery_task_id=task_id,
        max_attempts=settings.CELERY_TASK_MAX_RETRIES,
        target_id=doc.id

    )

    await update_document_status(db, document_id=doc.id, status="queued")
    queued_document = await get_document_by_id(
        db,
        document_id=doc.id,
    )
    if queued_document:
        await sync_document_projection_from_db(
            db,
            document=queued_document,
        )
    app_logger.bind(module="document_service").info(
        f"submit index task prepared task_id={task_id} document_id={doc.id} "
        f"knowledge_base_id={doc.knowledge_base_id}"
    )

    return {
        "task_id": task_id,
        "document_id": doc.id,
        "knowledge_base_id": doc.knowledge_base_id,
        "status": "pending",
        "message": "index task submitted",
    }





















