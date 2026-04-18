from datetime import datetime
from pathlib import Path
import shutil
import uuid
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from conf.config import settings
from conf.database import get_database
from crud.document import create_document, get_document_by_id, list_documents, update_document_status
from crud.knowledge_base import get_knowledge_base_by_id, get_or_create_default_knowledge_base
from crud.user import get_user_by_id
from infra.rate_limit import enforce_fixed_window_rate_limit
from schemas.document import DocumentListData, DocumentListItem, DocumentUploadData, DocumentIndexData, \
    DocumentIndexTaskData
from services.document_service import submit_document_index_task
from utils.exceptions import BusinessException
from utils.response import success_response

# 提供文档上传、列表查询和索引提交这几个入口接口。
router = APIRouter(prefix="/kb/documents", tags=["documents"])


# 生成文档公开 ID，供数据库和文件命名共同使用。
async def build_document_id() -> str:
    return f"doc_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"


# 确保原始文件存储目录存在，并返回目录路径。
async def ensure_storage_dir() -> Path:
    raw_dir = settings.RAW_FILE_DIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir


@router.post("/upload")
# 接收上传文件，完成基础校验、落盘和 documents 表入库。
async def upload_document(
        user_id: int = Form(...),
        knowledge_base_id: str | None = Form(default=None),
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_database),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise BusinessException(message="用户不存在", code=4041, status_code=404)

    enforce_fixed_window_rate_limit(
        bucket="document_upload",
        key=f"user:{user_id}",
        limit=settings.UPLOAD_RATE_LIMIT_MAX,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )







    knowledge_base = None
    if knowledge_base_id:
        knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id)
        if not knowledge_base:
            raise BusinessException(message="知识库不存在", code=4042, status_code=404)
        if knowledge_base.user_id != user_id:
            raise BusinessException(message="知识库不属于该用户", code=4007)
    else:
        knowledge_base = await get_or_create_default_knowledge_base(db, user_id=user_id)

    if not file.filename:
        raise BusinessException(message="上传失败，文件名不能为空", code=4001)

    file_name = Path(file.filename).name
    file_ext = Path(file_name).suffix.lower()

    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise BusinessException(message="wrong file type")

    files_size = file.size
    if files_size is None:
        file.file.seek(0, 2)
        files_size = file.file.tell()
        file.file.seek(0)

    if files_size == 0:
        raise BusinessException(message="上传失败，文件不能为空", code=4003)

    if files_size > settings.MAX_FILE_SIZE:
        raise BusinessException(message=f"The uploaded size of the file must be less than {settings.MAX_FILE_SIZE}")

    document_id = await build_document_id()
    raw_dir = await ensure_storage_dir()
    safe_name = file_name.replace(" ", "_")
    # save_path 形如 "storage/raw/doc_xxx__resume.pdf"，用于原始文件持久化。
    save_path = raw_dir / f"{document_id}__{safe_name}"

    try:
        with save_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        document = await create_document(
            db,
            document_id=document_id,
            user_id=user_id,
            knowledge_base_id=knowledge_base.id,
            knowledge_base_pk=knowledge_base.pk,
            file_name=file_name,
            file_path=str(save_path),
            file_type=file_ext.lstrip("."),
            file_size=files_size,
            status="uploaded",
        )
    except Exception as exc:
        if save_path.exists():
            save_path.unlink()
        raise BusinessException(message=f"上传失败：{exc}", code=5001, status_code=500)

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
# 按用户或知识库维度返回文档列表。
async def get_document_list(
        user_id: int | None = None,
        knowledge_base_id: str | None = None,
        db: AsyncSession = Depends(get_database),
):
    if user_id:
        user = await get_user_by_id(db, user_id)
        if not user:
            raise BusinessException(message="用户不存在", code=4041, status_code=404)

    knowledge_base = None
    if knowledge_base_id:
        knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id)
        if not knowledge_base:
            raise BusinessException(message="知识库不存在", code=4042, status_code=404)
        if user_id and knowledge_base.user_id != user_id:
            raise BusinessException(message="知识库不属于该用户", code=4007)

    documents = await list_documents(
        db,
        user_id=user_id,
        knowledge_base_pk=knowledge_base.pk if knowledge_base else None,
    )
    document_items = [
        DocumentListItem.model_validate(u)
        for u in documents
    ]

    total = len(document_items)
    data = DocumentListData(items=document_items, total=total)
    return success_response(data=data)




@router.post("/{document_id}/index")
# 提交单个文档的索引任务，并立即返回 task_id。
async def index_document_api(
        document_id: str,
        db: AsyncSession = Depends(get_database),
):
    result = await submit_document_index_task(
        db,
        document_id=document_id,
    )
    await db.commit()

    return success_response(
        data=DocumentIndexTaskData(**result),
        message="index task submitted",
    )



















