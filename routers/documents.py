from datetime import datetime
from pathlib import Path
import shutil
import uuid
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from conf.config import settings
from conf.database import get_database
from crud.document import create_document, list_documents,get_document_by_id,update_document_status
from schemas.document import DocumentListData, DocumentListItem, DocumentUploadData, DocumentIndexData
from utils.exceptions import BusinessException
from utils.response import success_response
from utils.index_service import index_document

router = APIRouter(prefix="/kb/documents", tags=["documents"])


async def build_document_id() -> str:
    return f"doc_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"


async def ensure_storage_dir() -> Path:
    raw_dir = settings.RAW_FILE_DIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir


@router.post("/upload")
async def upload_document(
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_database),
):
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
    save_path = raw_dir / f"{document_id}__{safe_name}"

    try:
        with save_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        document = await create_document(
            db,
            document_id=document_id,
            knowledge_base_id=None,
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
            file_name=document.file_name,
            file_type=document.file_type,
            file_size=document.file_size,
            status=document.status,
        ),
        message="upload success",
    )


@router.get("")
async def get_document_list(db: AsyncSession = Depends(get_database)):
    documents = await list_documents(db)
    document_items = [
        DocumentListItem.model_validate(u)
        for u in documents
    ]

    total = len(document_items)
    data = DocumentListData(items=document_items, total=total)
    return success_response(data=data)




@router.post("/{document_id}/index")
async def index_document_api(
        document_id: str,
        db: AsyncSession = Depends(get_database),
):
    # 你要做的事：
    # 1. 根据 document_id 查文档
    # 2. 如果文档不存在，抛 404
    # 3. 如果文档已经是 indexed，可以选择直接返回或提示重复索引
    # 4. 调用 index_document(db, document)
    # 5. 如果索引出错，把状态改成 failed
    # 6. 返回 success_response(...)
    doc = await get_document_by_id(db,document_id=document_id)
    if not doc:
        raise BusinessException(message="document not fund",status_code=404)

    if doc.status == "indexed":
        raise BusinessException(message="文档正在索引中，请稍后再试", code=4005)

    try:
        result = await index_document(db, doc)
    except Exception as exc:
        await update_document_status(db, document_id=document_id, status="failed")
        await db.commit()
        raise BusinessException(message=f"建立索引失败：{exc}", code=5002, status_code=500)

    return success_response(
        data=DocumentIndexData(**result),
        message="index successfully"
    )





















