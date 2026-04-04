from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from crud.memory_entry import list_memory_entries_by_document_id
from conf.database import get_database
from schemas.memory_library import MemoryLibraryData
from utils.memory_organizer import build_memory_library
from utils.response import success_response


router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/{document_id}/library")
async def get_memory_library(
        document_id: str,
        db: AsyncSession = Depends(get_database),
):
    rows = await list_memory_entries_by_document_id(
        db,
        document_id=document_id,
    )

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
    data = MemoryLibraryData(**memory_library)

    return success_response(data=data)
















