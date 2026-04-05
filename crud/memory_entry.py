from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.memory_entry import MemoryEntry


async def create_memory_entries(
        db: AsyncSession,
        *,
        entries: list[dict],
) -> list[MemoryEntry]:

    memory_list = [MemoryEntry(**item) for item in entries]

    db.add_all(memory_list)
    await db.flush()
    return memory_list





async def list_memory_entries_by_document_id(
        db: AsyncSession,
        *,
        document_id: str,
) -> list[MemoryEntry]:
    sql = (
        select(MemoryEntry)
        .where(MemoryEntry.document_id == document_id)
        .order_by(MemoryEntry.created_at.asc())
    )
    res = await db.execute(sql)
    return list(res.scalars().all())


async def list_memory_entries_by_knowledge_base_id(
        db: AsyncSession,
        *,
        knowledge_base_id: str,
) -> list[MemoryEntry]:
    sql = (
        select(MemoryEntry)
        .where(MemoryEntry.knowledge_base_id == knowledge_base_id)
        .order_by(MemoryEntry.created_at.asc())
    )
    res = await db.execute(sql)
    return list(res.scalars().all())


async def list_memory_entries_by_user_id(
        db: AsyncSession,
        *,
        user_id: int,
) -> list[MemoryEntry]:
    sql = (
        select(MemoryEntry)
        .where(MemoryEntry.user_id == user_id)
        .order_by(MemoryEntry.created_at.asc())
    )
    res = await db.execute(sql)
    return list(res.scalars().all())























