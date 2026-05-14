from langchain_core.documents import Document as LCDocument
from sqlalchemy import delete, insert, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models import Document
from models.chunk import Chunk

BULK_INSERT_BATCH_SIZE = 5000


# 将切分后的 chunk 批量写入 chunks 表。
async def create_chunks(
        db: AsyncSession,
        *,
        document_id: str,
        document_pk: int,
        chunk_docs: list[LCDocument],
) -> None:
    # rows 会被整理成适合 bulk insert 的扁平结构，形如：
    # {
    #     "id": "doc_demo_001_chunk_0_a1b2c3",
    #     "document_id": "doc_demo_001",
    #     "document_pk": 1,
    #     "chunk_index": 0,
    #     "content": "第一段 chunk 文本",
    #     "page_no": 1,
    #     "start_offset": 0,
    #     "end_offset": 120,
    # }
    rows: list[dict] = []
    stmt = insert(Chunk).execution_options(render_nulls=True)

    for chunk in chunk_docs:
        content = chunk.page_content.strip()
        if not content:
            continue

        start_offset = chunk.metadata.get("start_offset")
        end_offset = (
            start_offset + len(content)
            if isinstance(start_offset,int)
            else None
        )


        rows.append(
            {
                "id": chunk.metadata["chunk_id"],
                "document_id": document_id,
                "document_pk": document_pk,
                "chunk_index": chunk.metadata["chunk_index"],
                "content": content,
                "page_no": chunk.metadata["page_no"],
                "start_offset": start_offset,
                "end_offset": end_offset,
            }
        )

        if len(rows) >= BULK_INSERT_BATCH_SIZE:
            await db.execute(stmt, rows)
            rows.clear()

    if rows:
        await db.execute(stmt, rows)


async def list_chunks_by_document_id(
        db: AsyncSession,
        *,
        document_id: str,
) -> list[Chunk]:
    sql = (
        select(Chunk)
        .where(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index.asc())
    )
    res = await db.execute(sql)
    return list(res.scalars().all())


async def delete_chunks_by_document_id(
        db: AsyncSession,
        *,
        document_id: str,
) -> int:
    sql = delete(Chunk).where(Chunk.document_id == document_id)
    res = await db.execute(sql)
    return res.rowcount or 0


async def search_chunks_by_keywords(
    db: AsyncSession,
    *,
    knowledge_base_id: str,
    user_id: int | None = None,
    query_terms: list[str],
    limit: int = 6,
) -> list[Chunk]:
    terms = [term.strip() for term in query_terms if term and term.strip()]
    if not terms:
        return []

    document_table = Document.__table__
    conditions = [Chunk.content.ilike(f"%{term}%") for term in terms]
    sql = select(Chunk).join(document_table, Chunk.document_pk == document_table.c.pk).where(
        document_table.c.knowledge_base_id == knowledge_base_id,
        or_(*conditions),
    )
    if user_id is not None:
        sql = sql.where(document_table.c.user_id == user_id)

    sql = sql.order_by(Chunk.document_pk.asc(), Chunk.chunk_index.asc()).limit(limit)
    res = await db.execute(sql)
    return list(res.scalars().all())







