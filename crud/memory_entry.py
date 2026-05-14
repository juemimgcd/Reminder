from sqlalchemy import delete, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from crud.document import get_document_by_id
from crud.knowledge_base import get_knowledge_base_by_id
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
    document = await get_document_by_id(db, document_id=document_id)
    if not document:
        return []

    sql = (
        select(MemoryEntry)
        .where(MemoryEntry.document_pk == document.pk)
        .order_by(MemoryEntry.created_at.asc())
    )
    res = await db.execute(sql)
    return list(res.scalars().all())


async def list_memory_entries_by_knowledge_base_id(
        db: AsyncSession,
        *,
        knowledge_base_id: str,
) -> list[MemoryEntry]:
    knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id=knowledge_base_id)
    if not knowledge_base:
        return []

    sql = (
        select(MemoryEntry)
        .where(MemoryEntry.knowledge_base_pk == knowledge_base.pk)
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


async def delete_memory_entries_by_document_id(
        db: AsyncSession,
        *,
        document_id: str,
) -> int:
    document = await get_document_by_id(db, document_id=document_id)
    if not document:
        return 0

    sql = delete(MemoryEntry).where(MemoryEntry.document_pk == document.pk)
    res = await db.execute(sql)
    return res.rowcount or 0


async def delete_memory_entries_by_knowledge_base_id(
        db: AsyncSession,
        *,
        knowledge_base_id: str,
) -> int:
    knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id=knowledge_base_id)
    if not knowledge_base:
        return 0

    sql = delete(MemoryEntry).where(MemoryEntry.knowledge_base_pk == knowledge_base.pk)
    res = await db.execute(sql)
    return res.rowcount or 0




async def search_memory_entries_by_keywords(
    db: AsyncSession,
    *,
    knowledge_base_id: str,
    user_id: int | None = None,
    query_terms: list[str],
    limit: int = 6,
) -> list[MemoryEntry]:
    terms = [term.strip() for term in query_terms if term and term.strip()]
    if not terms:
        return []

    memory_entry_table = MemoryEntry.__table__
    field_conditions = []
    for term in terms:
        field_conditions.extend(
            [
                MemoryEntry.entry_name.ilike(f"%{term}%"),
                MemoryEntry.summary.ilike(f"%{term}%"),
                MemoryEntry.evidence_text.ilike(f"%{term}%"),
            ]
        )

    sql = (
        select(MemoryEntry)
        .where(memory_entry_table.c.knowledge_base_id == knowledge_base_id)
        .where(or_(*field_conditions))
    )
    if user_id is not None:
        sql = sql.where(memory_entry_table.c.user_id == user_id)

    sql = sql.order_by(MemoryEntry.importance_score.desc(), MemoryEntry.document_pk.asc()).limit(limit)
    res = await db.execute(sql)
    return list(res.scalars().all())


















