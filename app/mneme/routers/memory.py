from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.database import get_database, get_write_database
from app.mneme.conf.logging import app_logger
from app.mneme.crud.document import get_document_by_id
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id
from app.mneme.crud.memory_entry import (
    list_memory_entries_by_document_id,
    list_memory_entries_by_knowledge_base_id,
)
from app.mneme.models.user import User
from app.mneme.schemas.memory_library import MemoryLibraryData, MemoryRebuildData
from app.mneme.schemas.memory_governance import MemoryGovernanceData
from app.mneme.services.memory_governance_service import build_memory_governance_view
from app.mneme.services.memory_service import build_memory_library, rebuild_memory_entries_for_knowledge_base
from app.mneme.utils.auth import get_current_user
from app.mneme.utils.exceptions import BusinessException
from app.mneme.utils.response import success_response


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
        raise BusinessException(message="knowledge base not found", code=4042, status_code=404)
    if knowledge_base.user_id != current_user.id:
        raise BusinessException(message="knowledge base does not belong to current user", code=4007)

    rows = await list_memory_entries_by_knowledge_base_id(
        db,
        knowledge_base_id=knowledge_base_id,
    )
    app_logger.bind(module="memory_router").info(
        f"memory library success knowledge_base_id={knowledge_base_id} entry_count={len(rows)}"
    )
    data = build_memory_library_response(rows)
    return success_response(data=data)


@router.get("/knowledge-bases/{knowledge_base_id}/governance")
async def get_memory_governance(
        knowledge_base_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="memory_router").info(
        f"memory governance request knowledge_base_id={knowledge_base_id} current_user_id={current_user.id}"
    )
    knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id)
    if not knowledge_base:
        raise BusinessException(message="knowledge base not found", code=4042, status_code=404)
    if knowledge_base.user_id != current_user.id:
        raise BusinessException(message="knowledge base does not belong to current user", code=4007)

    rows = await list_memory_entries_by_knowledge_base_id(
        db,
        knowledge_base_id=knowledge_base_id,
    )
    data = build_memory_governance_view(
        knowledge_base_id=knowledge_base_id,
        entries=rows,
    )
    app_logger.bind(module="memory_router").info(
        f"memory governance success knowledge_base_id={knowledge_base_id} "
        f"raw_entry_count={data.raw_entry_count} canonical_memory_count={data.canonical_memory_count}"
    )
    return success_response(
        data=MemoryGovernanceData.model_validate(data),
        message="memory governance built",
    )


@router.post("/knowledge-bases/{knowledge_base_id}/rebuild")
async def rebuild_memory_library(
        knowledge_base_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_write_database),
):
    app_logger.bind(module="memory_router").info(
        f"memory rebuild request knowledge_base_id={knowledge_base_id} current_user_id={current_user.id}"
    )
    knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id)
    if not knowledge_base:
        raise BusinessException(message="knowledge base not found", code=4042, status_code=404)
    if knowledge_base.user_id != current_user.id:
        raise BusinessException(message="knowledge base does not belong to current user", code=4007)

    result = await rebuild_memory_entries_for_knowledge_base(
        knowledge_base_pk=knowledge_base.pk,
        knowledge_base_id=knowledge_base.id,
    )
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
        raise BusinessException(message="鏂囨。涓嶅瓨鍦ㄦ垨涓嶅睘浜庤鐢ㄦ埛", code=4044, status_code=404)

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
