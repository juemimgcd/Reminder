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


# 鏍￠獙鏂囨。鏄惁瀛樺湪锛屼互鍙婂綋鍓嶇姸鎬佹槸鍚﹀厑璁稿啀娆¤繘鍏ョ储寮曘€?
async def ensure_document_can_index(
        db: AsyncSession,
        *,
        document_id: str,
) -> Document:
    # 浣犺鍋氱殑浜嬶細
    # 1. 璇?document
    # 2. 鍒ゆ柇鏄惁瀛樺湪
    # 3. 鍒ゆ柇褰撳墠鐘舵€佹槸鍚﹀厑璁歌繘鍏ョ储寮?
    # 4. 杩斿洖 document
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



# 鐢熸垚鏂囨。绱㈠紩浠诲姟浣跨敤鐨?task_id銆?
def build_index_task_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"task_index_{timestamp}_{uuid.uuid4().hex[:6]}"






# 鎻愪氦鏂囨。绱㈠紩浠诲姟锛屽苟鍦ㄥ叆闃熷墠瀹屾垚闄愭祦鍜岀姸鎬佹牎楠屻€?
async def submit_document_index_task(
        db: AsyncSession,
        *,
        document_id: str,
) -> dict:
    # 浣犺鍋氱殑浜嬶細
    # 1. 鏍￠獙 document 鏄惁瀛樺湪銆佹槸鍚﹀彲绱㈠紩
    # 2. 鐢熸垚 task_id
    # 3. 鍒涘缓 task_record
    # 4. 鏇存柊 document.status 涓?queued
    # 5. 鐢辫皟鐢ㄦ柟鍦?commit 鍚庢姇閫掍换鍔?
    # 6. 杩斿洖浠诲姟鎻愪氦缁撴灉
    doc = await ensure_document_can_index(
        db,
        document_id=document_id,
    )
    app_logger.bind(module="document_service").info(
        f"submit index task start document_id={doc.id} user_id={doc.user_id} "
        f"knowledge_base_id={doc.knowledge_base_id} status={doc.status}"
    )

    # 杩欓噷鐨勯檺娴?key 褰㈠ "user:1:kb:kb_demo_001"锛岀敤浜庨檺鍒堕噸澶嶇储寮曟彁浜ゃ€?
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





















