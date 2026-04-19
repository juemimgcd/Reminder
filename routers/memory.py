from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from conf.database import get_database
from conf.logging import app_logger
from crud.document import get_document_by_id
from crud.knowledge_base import get_knowledge_base_by_id
from crud.memory_entry import (
    list_memory_entries_by_document_id,
    list_memory_entries_by_knowledge_base_id,
)
from models.user import User
from schemas.memory_library import MemoryLibraryData, MemoryRebuildData
from services.memory_service import build_memory_library, rebuild_memory_entries_for_knowledge_base
from utils.auth import get_current_user
from utils.exceptions import BusinessException
from utils.response import success_response


router = APIRouter(prefix="/memory", tags=["memory"])


def build_memory_library_response(rows) -> MemoryLibraryData:
    entries = [
        {
            "id": item.id,
            "entry_name": item.entry_name,
            "entry_type": item.entry_type,
            "summary": item.summary,
            "created_at": item.created_at,
        }
        for item in rows
    ]

    memory_library = build_memory_library(entries)
    return MemoryLibraryData(**memory_library)


@router.get("/knowledge-bases/{knowledge_base_id}/library")
async def get_memory_library(
        knowledge_base_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="memory_router").info(
        f"memory library request knowledge_base_id={knowledge_base_id} current_user_id={current_user.id}"
    )
    knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id)
    if not knowledge_base:
        raise BusinessException(message="知识库不存在", code=4042, status_code=404)
    if knowledge_base.user_id != current_user.id:
        raise BusinessException(message="知识库不属于该用户", code=4007)

    rows = await list_memory_entries_by_knowledge_base_id(
        db,
        knowledge_base_id=knowledge_base_id,
    )
    app_logger.bind(module="memory_router").info(
        f"memory library success knowledge_base_id={knowledge_base_id} entry_count={len(rows)}"
    )
    data = build_memory_library_response(rows)
    return success_response(data=data)


@router.post("/knowledge-bases/{knowledge_base_id}/rebuild")
async def rebuild_memory_library(
        knowledge_base_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="memory_router").info(
        f"memory rebuild request knowledge_base_id={knowledge_base_id} current_user_id={current_user.id}"
    )
    knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id)
    if not knowledge_base:
        raise BusinessException(message="知识库不存在", code=4042, status_code=404)
    if knowledge_base.user_id != current_user.id:
        raise BusinessException(message="知识库不属于该用户", code=4007)

    result = await rebuild_memory_entries_for_knowledge_base(
        db,
        knowledge_base_pk=knowledge_base.pk,
        knowledge_base_id=knowledge_base.id,
    )
    await db.commit()
    app_logger.bind(module="memory_router").info(
        f"memory rebuild success knowledge_base_id={knowledge_base_id} "
        f"processed_document_count={result['processed_document_count']} entry_count={result['entry_count']}"
    )
    return success_response(
        data=MemoryRebuildData(**result),
        message="memory rebuild completed",
    )


@router.get("/documents/{document_id}/library")
async def get_document_memory_library(
        document_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="memory_router").info(
        f"document memory library request document_id={document_id} current_user_id={current_user.id}"
    )
    document = await get_document_by_id(
        db,
        document_id=document_id,
        user_id=current_user.id,
    )
    if not document:
        raise BusinessException(message="文档不存在或不属于该用户", code=4044, status_code=404)

    rows = await list_memory_entries_by_document_id(
        db,
        document_id=document_id,
    )

    app_logger.bind(module="memory_router").info(
        f"document memory library success document_id={document_id} "
        f"current_user_id={current_user.id} entry_count={len(rows)}"
    )
    data = build_memory_library_response(rows)
    return success_response(data=data)
