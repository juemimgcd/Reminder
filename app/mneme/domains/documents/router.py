from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.config import settings
from app.mneme.conf.database import get_database, get_write_database
from app.mneme.conf.logging import app_logger
from app.mneme.crud.document import get_document_by_id, list_documents
from app.mneme.crud.document_folder import ensure_root_folder, get_folder_by_id, get_folder_by_pk
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id, get_or_create_default_knowledge_base
from app.mneme.infra.rate_limit import enforce_fixed_window_rate_limit
from app.mneme.infra.task_queue import enqueue_index_document_task
from app.mneme.models.chunk import Chunk
from app.mneme.models.document import Document
from app.mneme.models.memory import MemoryEntry
from app.mneme.models.user import User
from app.mneme.schemas.document import (
    DocumentDeleteData,
    DocumentListData,
    DocumentListItem,
    DocumentIndexTaskData,
    DocumentPreviewChunk,
    DocumentPreviewData,
    DocumentPreviewMemoryEntry,
    DocumentVersionData,
    DocumentVersionListData,
)
from app.mneme.domains.documents.content_service import (
    build_document_content,
    list_document_versions,
    require_source_file,
    sanitize_download_name,
)
from app.mneme.domains.documents.service import submit_document_index_task
from app.mneme.domains.documents.resources import delete_document_resources
from app.mneme.domains.documents.upload_service import store_uploaded_document
from app.mneme.domains.graph.projection import sync_document_projection
from app.mneme.utils.auth import get_current_user
from app.mneme.utils.exceptions import BusinessException
from app.mneme.utils.response import success_response


router = APIRouter(prefix="/kb/documents", tags=["documents"])


def ensure_user_context_matches(current_user: User, raw_user_id: int | None) -> int:
    if raw_user_id is not None and raw_user_id != current_user.id:
        raise BusinessException(message="user context does not match current user", code=4008, status_code=403)
    return current_user.id


def summarize_document_preview(chunks: list[Chunk], memory_entries: list[MemoryEntry]) -> str:
    if memory_entries:
        return memory_entries[0].summary
    for chunk in chunks:
        if chunk.section_summary:
            return chunk.section_summary
        if chunk.content:
            return chunk.content[:360]
    return "No indexed preview content is available for this document yet."


async def require_owned_document(db: AsyncSession, document_id: str, user_id: int) -> Document:
    document = await get_document_by_id(db, document_id=document_id, user_id=user_id)
    if document is None:
        raise BusinessException(
            message="document not found or not owned by current user",
            code=4044,
            status_code=404,
        )
    return document


@router.post("/upload")
async def upload_document(
        user_id: int | None = Form(default=None),
        knowledge_base_id: str | None = Form(default=None),
        folder_id: str | None = Form(default=None),
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_write_database),
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
            raise BusinessException(message="knowledge base not found", code=4042, status_code=404)
        if knowledge_base.user_id != resolved_user_id:
            raise BusinessException(message="knowledge base does not belong to current user", code=4007)
    else:
        knowledge_base = await get_or_create_default_knowledge_base(db, user_id=resolved_user_id)

    root = await ensure_root_folder(
        db,
        user_id=resolved_user_id,
        knowledge_base_id=knowledge_base.id,
        knowledge_base_pk=knowledge_base.pk,
    )
    folder = root
    if folder_id is not None:
        folder = await get_folder_by_id(db, folder_id=folder_id, user_id=resolved_user_id)
        if folder is None or folder.knowledge_base_pk != knowledge_base.pk:
            raise BusinessException(message="folder not found in knowledge base", code=4045, status_code=404)

    # Legacy uploads with no folder_id continue to resolve folder_pk=root.pk.
    upload_data = await store_uploaded_document(
        db,
        file=file,
        current_user=current_user,
        knowledge_base=knowledge_base,
        folder=folder,
    )
    document = None
    try:
        if upload_data.disposition == "created":
            document = await get_document_by_id(
                db,
                upload_data.document_id,
                user_id=resolved_user_id,
                knowledge_base_pk=knowledge_base.pk,
            )
            if document is None:
                raise RuntimeError("created document could not be resolved")
            await sync_document_projection(
                user=current_user,
                knowledge_base=knowledge_base,
                document=document,
            )
    except Exception as exc:
        if document is not None:
            Path(document.file_path).unlink(missing_ok=True)
        app_logger.bind(module="documents_router").exception(
            f"upload projection failed user_id={resolved_user_id} knowledge_base_id={knowledge_base.id} "
            f"document_id={upload_data.document_id} error={exc}"
        )
        raise BusinessException(message="upload projection failed", code=5001, status_code=500) from exc

    app_logger.bind(module="documents_router").info(
        f"upload success disposition={upload_data.disposition} document_id={upload_data.document_id} "
        f"user_id={resolved_user_id} knowledge_base_id={knowledge_base.id}"
    )
    return success_response(
        data=upload_data,
        message="upload success" if upload_data.disposition == "created" else "file already exists",
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
            raise BusinessException(message="knowledge base not found", code=4042, status_code=404)
        if knowledge_base.user_id != resolved_user_id:
            raise BusinessException(message="knowledge base does not belong to current user", code=4007)

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
        db: AsyncSession = Depends(get_write_database),
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
        raise BusinessException(message="document not found or not owned by current user", code=4044, status_code=404)

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


@router.get("/{document_id}/preview")
async def preview_document_api(
        document_id: str,
        chunk_limit: int = Query(default=5, ge=1, le=12),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    document = await get_document_by_id(
        db,
        document_id=document_id,
        user_id=current_user.id,
    )
    if not document:
        raise BusinessException(message="document not found or not owned by current user", code=4044, status_code=404)

    chunk_result = await db.execute(
        select(Chunk)
        .where(Chunk.document_pk == document.pk)
        .order_by(Chunk.chunk_index.asc())
        .limit(chunk_limit)
    )
    chunks = list(chunk_result.scalars().all())

    memory_result = await db.execute(
        select(MemoryEntry)
        .where(MemoryEntry.document_pk == document.pk)
        .order_by(MemoryEntry.importance_score.desc())
        .limit(5)
    )
    memory_entries = list(memory_result.scalars().all())

    return success_response(
        data=DocumentPreviewData(
            document_id=document.id,
            knowledge_base_id=document.knowledge_base_id,
            file_name=document.file_name,
            file_type=document.file_type,
            status=document.status,
            summary=summarize_document_preview(chunks, memory_entries),
            chunks=[
                DocumentPreviewChunk(
                    chunk_id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.content[:800],
                    page_no=chunk.page_no,
                    section_title=chunk.section_title,
                )
                for chunk in chunks
            ],
            memory_entries=[
                DocumentPreviewMemoryEntry(
                    entry_id=entry.id,
                    entry_name=entry.entry_name,
                    entry_type=entry.entry_type,
                    summary=entry.summary,
                    importance_score=entry.importance_score,
                )
                for entry in memory_entries
            ],
        )
    )


@router.get("/{document_id}/content")
async def document_content_api(
        document_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    document = await require_owned_document(db, document_id, current_user.id)
    folder = await get_folder_by_pk(db, folder_pk=document.folder_pk, user_id=current_user.id)
    if folder is None:
        raise BusinessException(
            message="document folder is unavailable",
            code=4045,
            status_code=404,
        )
    return success_response(
        data=await build_document_content(document, folder_id=folder.id)
    )


@router.get("/{document_id}/raw")
async def document_raw_api(
        document_id: str,
        disposition: Literal["inline", "attachment"] = Query(default="inline"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    document = await require_owned_document(db, document_id, current_user.id)
    source_path = require_source_file(document)
    is_pdf = document.file_type.strip().lower().lstrip(".") == "pdf"
    effective_disposition = "inline" if is_pdf and disposition == "inline" else "attachment"
    media_type = "application/pdf" if is_pdf else "application/octet-stream"
    return FileResponse(
        source_path,
        media_type=media_type,
        content_disposition_type=effective_disposition,
        filename=sanitize_download_name(document.file_name),
    )


@router.get("/{document_id}/versions")
async def document_versions_api(
        document_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    document = await require_owned_document(db, document_id, current_user.id)
    versions = await list_document_versions(
        db,
        version_group_id=document.version_group_id,
        user_id=current_user.id,
    )
    items = [
        DocumentVersionData(
            document_id=version.id,
            version_group_id=version.version_group_id,
            version_number=version.version_number,
            file_name=version.file_name,
            created_at=version.created_at,
        )
        for version in versions
    ]
    return success_response(data=DocumentVersionListData(items=items, total=len(items)))


@router.delete("/{document_id}")
async def delete_document_api(
        document_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_write_database),
):
    document = await get_document_by_id(
        db,
        document_id=document_id,
        user_id=current_user.id,
    )
    if not document:
        raise BusinessException(message="document not found or not owned by current user", code=4044, status_code=404)

    if document.status in {"queued", "indexing", "parsing", "chunking", "embedding", "vector_upserting"}:
        raise BusinessException(message="cancel or wait for index tasks before deleting the document", code=4021, status_code=400)

    result = await delete_document_resources(
        db,
        document=document,
    )
    return success_response(
        data=DocumentDeleteData(**result),
        message="document deleted",
    )
