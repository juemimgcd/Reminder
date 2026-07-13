from sqlalchemy import case, delete, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.crud.document import get_document_by_id
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id
from app.mneme.domains.memory.identity import prepare_memory_entry_payload
from app.mneme.models.memory_entry import MemoryEntry


async def create_memory_entries(
        db: AsyncSession,
        *,
        entries: list[dict],
) -> list[MemoryEntry]:

    memory_list = [MemoryEntry(**prepare_memory_entry_payload(item)) for item in entries]

    db.add_all(memory_list)
    await db.flush()
    return memory_list





async def list_memory_entries_by_document_id(
        db: AsyncSession,
        *,
        document_id: str,
        include_inactive: bool = False,
) -> list[MemoryEntry]:
    document = await get_document_by_id(db, document_id=document_id)
    if not document:
        return []

    sql = select(MemoryEntry).where(MemoryEntry.document_pk == document.pk)
    if not include_inactive:
        sql = sql.where(MemoryEntry.status == "active")
    sql = sql.order_by(MemoryEntry.created_at.asc())
    res = await db.execute(sql)
    return list(res.scalars().all())


async def list_memory_entries_by_knowledge_base_id(
        db: AsyncSession,
        *,
        knowledge_base_id: str,
        include_inactive: bool = False,
) -> list[MemoryEntry]:
    knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id=knowledge_base_id)
    if not knowledge_base:
        return []

    sql = select(MemoryEntry).where(MemoryEntry.knowledge_base_pk == knowledge_base.pk)
    if not include_inactive:
        sql = sql.where(MemoryEntry.status == "active")
    sql = sql.order_by(MemoryEntry.created_at.asc())
    res = await db.execute(sql)
    return list(res.scalars().all())


async def list_memory_entries_by_user_id(
        db: AsyncSession,
        *,
        user_id: int,
        include_inactive: bool = False,
) -> list[MemoryEntry]:
    sql = select(MemoryEntry).where(MemoryEntry.user_id == user_id)
    if not include_inactive:
        sql = sql.where(MemoryEntry.status == "active")
    sql = sql.order_by(MemoryEntry.created_at.asc())
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
) -> list[tuple[MemoryEntry, float]]:
    terms = [term.strip() for term in query_terms if term and term.strip()]
    if not terms:
        return []

    memory_entry_table = MemoryEntry.__table__
    field_conditions = []
    score_expr = literal(0.0)
    for term in terms:
        entry_name_match = MemoryEntry.entry_name.ilike(f"%{term}%")
        summary_match = MemoryEntry.summary.ilike(f"%{term}%")
        evidence_match = MemoryEntry.evidence_text.ilike(f"%{term}%")
        field_conditions.extend(
            [
                entry_name_match,
                summary_match,
                evidence_match,
            ]
        )
        score_expr += case((entry_name_match, 1.0), else_=0.0)
        score_expr += case((summary_match, 0.8), else_=0.0)
        score_expr += case((evidence_match, 0.9), else_=0.0)

    score_label = score_expr.label("keyword_score")
    sql = (
        select(MemoryEntry, score_label)
        .where(memory_entry_table.c.knowledge_base_id == knowledge_base_id)
        .where(memory_entry_table.c.status == "active")
        .where(or_(*field_conditions))
    )
    if user_id is not None:
        sql = sql.where(memory_entry_table.c.user_id == user_id)

    sql = sql.order_by(
        score_label.desc(),
        MemoryEntry.importance_score.desc(),
        MemoryEntry.document_pk.asc(),
    ).limit(limit)
    res = await db.execute(sql)
    return [(row[0], float(row[1] or 0.0)) for row in res.all()]


















