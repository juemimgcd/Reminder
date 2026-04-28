from datetime import datetime
from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from conf.config import settings
from conf.database import get_database
from conf.logging import app_logger
from crud.document import create_document, get_document_by_id, list_documents
from crud.knowledge_base import get_knowledge_base_by_id, get_or_create_default_knowledge_base
from infra.rate_limit import enforce_fixed_window_rate_limit
from infra.task_queue import enqueue_index_document_task
from models.user import User
from schemas.document import DocumentDeleteData, DocumentListData, DocumentListItem, DocumentIndexTaskData, DocumentUploadData
from services.document_service import submit_document_index_task
from services.graph_projection_service import sync_document_projection
from services.resource_service import delete_document_resources
from utils.auth import get_current_user
from utils.exceptions import BusinessException
from utils.response import success_response


router = APIRouter(prefix="/kb/documents", tags=["documents"])


async def build_document_id() -> str:
    return f"doc_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"


async def ensure_storage_dir() -> Path:
    raw_dir = settings.RAW_FILE_DIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir


def ensure_user_context_matches(current_user: User, raw_user_id: int | None) -> int:
    if raw_user_id is not None and raw_user_id != current_user.id:
        raise BusinessException(message="用户上下文不一致", code=4008, status_code=403)
    return current_user.id


@router.post("/upload")
async def upload_document(
        user_id: int | None = Form(default=None),
        knowledge_base_id: str | None = Form(default=None),
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    resolved_user_id = ensure_user_context_matches(current_user, user_id)
    app_logger.bind(module="documents_router").info(
        f"upload request received user_id={resolved_user_id} knowledge_base_id={knowledge_base_id} "
        f"filename={file.filename}"
    )

    enforce_fixed_window_rate_limit(
        bucket="document_upload",
        key=f"user:{resolved_user_id}",
        limit=settings.UPLOAD_RATE_LIMIT_MAX,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )

    if knowledge_base_id:
        knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id)
        if not knowledge_base:
            raise BusinessException(message="知识库不存在", code=4042, status_code=404)
        if knowledge_base.user_id != resolved_user_id:
            raise BusinessException(message="知识库不属于该用户", code=4007)
    else:
        knowledge_base = await get_or_create_default_knowledge_base(db, user_id=resolved_user_id)

    if not file.filename:
        raise BusinessException(message="上传失败，文件名不能为空", code=4001)

    file_name = Path(file.filename).name
    file_ext = Path(file_name).suffix.lower()

    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise BusinessException(message="wrong file type")

    file_size = file.size
    if file_size is None:
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)

    if file_size == 0:
        raise BusinessException(message="上传失败，文件不能为空", code=4003)

    if file_size > settings.MAX_FILE_SIZE:
        raise BusinessException(message=f"The uploaded size of the file must be less than {settings.MAX_FILE_SIZE}")

    document_id = await build_document_id()
    raw_dir = await ensure_storage_dir()
    safe_name = file_name.replace(" ", "_")
    save_path = raw_dir / f"{document_id}__{safe_name}"

    try:
        with save_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        document = await create_document(
            db,
            document_id=document_id,
            user_id=resolved_user_id,
            knowledge_base_id=knowledge_base.id,
            knowledge_base_pk=knowledge_base.pk,
            file_name=file_name,
            file_path=str(save_path),
            file_type=file_ext.lstrip("."),
            file_size=file_size,
            status="uploaded",
        )
        await sync_document_projection(
            user=current_user,
            knowledge_base=knowledge_base,
            document=document,
        )
    except Exception as exc:
        if save_path.exists():
            save_path.unlink()
        app_logger.bind(module="documents_router").exception(
            f"upload failed user_id={resolved_user_id} knowledge_base_id={knowledge_base.id} "
            f"filename={file_name} error={exc}"
        )
        raise BusinessException(message=f"上传失败：{exc}", code=5001, status_code=500)

    app_logger.bind(module="documents_router").info(
        f"upload success document_id={document.id} user_id={document.user_id} "
        f"knowledge_base_id={document.knowledge_base_id} file_type={document.file_type} "
        f"file_size={document.file_size}"
    )

    return success_response(
        data=DocumentUploadData(
            document_id=document.id,
            user_id=document.user_id,
            knowledge_base_id=document.knowledge_base_id,
            file_name=document.file_name,
            file_type=document.file_type,
            file_size=document.file_size,
            status=document.status,
        ),
        message="upload success",
    )


@router.get("")
async def get_document_list(
        user_id: int | None = Query(default=None),
        knowledge_base_id: str | None = Query(default=None),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    resolved_user_id = ensure_user_context_matches(current_user, user_id)
    app_logger.bind(module="documents_router").info(
        f"list documents request user_id={resolved_user_id} knowledge_base_id={knowledge_base_id}"
    )

    knowledge_base = None
    if knowledge_base_id:
        knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id)
        if not knowledge_base:
            raise BusinessException(message="知识库不存在", code=4042, status_code=404)
        if knowledge_base.user_id != resolved_user_id:
            raise BusinessException(message="知识库不属于该用户", code=4007)

    documents = await list_documents(
        db,
        user_id=resolved_user_id,
        knowledge_base_pk=knowledge_base.pk if knowledge_base else None,
    )
    document_items = [DocumentListItem.model_validate(item) for item in documents]

    total = len(document_items)
    app_logger.bind(module="documents_router").info(
        f"list documents success user_id={resolved_user_id} knowledge_base_id={knowledge_base_id} total={total}"
    )
    data = DocumentListData(items=document_items, total=total)
    return success_response(data=data)


@router.post("/{document_id}/index")
async def index_document_api(
        document_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="documents_router").info(
        f"index request received document_id={document_id} current_user_id={current_user.id}"
    )
    document = await get_document_by_id(
        db,
        document_id=document_id,
        user_id=current_user.id,
    )
    if not document:
        raise BusinessException(message="文档不存在或不属于该用户", code=4044, status_code=404)

    result = await submit_document_index_task(
        db,
        document_id=document_id,
    )
    await db.commit()
    enqueue_index_document_task(
        task_id=result["task_id"],
        document_id=document_id,
    )
    app_logger.bind(module="documents_router").info(
        f"index request committed task_id={result['task_id']} document_id={document_id}"
    )

    return success_response(
        data=DocumentIndexTaskData(**result),
        message="index task submitted",
    )


@router.delete("/{document_id}")
async def delete_document_api(
        document_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    document = await get_document_by_id(
        db,
        document_id=document_id,
        user_id=current_user.id,
    )
    if not document:
        raise BusinessException(message="文档不存在或不属于该用户", code=4044, status_code=404)

    if document.status in {"queued", "indexing", "parsing", "chunking", "embedding", "vector_upserting"}:
        raise BusinessException(message="请先取消或等待索引任务结束后再删除文档", code=4021, status_code=400)

    result = await delete_document_resources(
        db,
        document=document,
    )
    await db.commit()
    return success_response(
        data=DocumentDeleteData(**result),
        message="document deleted",
    )
