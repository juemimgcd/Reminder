from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from conf.database import get_database
from crud.knowledge_base import get_knowledge_base_by_id
from crud.memory_entry import (
    list_memory_entries_by_document_id,
    list_memory_entries_by_knowledge_base_id,
)
from schemas.memory_library import MemoryLibraryData
from utils.exceptions import BusinessException
from services.memory_service import build_memory_library
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
        user_id: int | None = None,
        db: AsyncSession = Depends(get_database),
):
    knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id)
    if not knowledge_base:
        raise BusinessException(message="知识库不存在", code=4042, status_code=404)
    if user_id and knowledge_base.user_id != user_id:
        raise BusinessException(message="知识库不属于该用户", code=4007)

    rows = await list_memory_entries_by_knowledge_base_id(
        db,
        knowledge_base_id=knowledge_base_id,
    )
    data = build_memory_library_response(rows)
    return success_response(data=data)


@router.get("/documents/{document_id}/library")
async def get_document_memory_library(
        document_id: str,
        db: AsyncSession = Depends(get_database),
):
    rows = await list_memory_entries_by_document_id(
        db,
        document_id=document_id,
    )

    data = build_memory_library_response(rows)
    return success_response(data=data)
















