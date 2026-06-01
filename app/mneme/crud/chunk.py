from langchain_core.documents import Document as LCDocument
from sqlalchemy import case, delete, insert, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.models import Document
from app.mneme.models.chunk import Chunk


BULK_INSERT_BATCH_SIZE = 5000


async def create_chunks(
    db: AsyncSession,
    *,
    document_id: str,
    document_pk: int,
    chunk_docs: list[LCDocument],
) -> None:
    rows: list[dict[str, object]] = []
    stmt = insert(Chunk).execution_options(render_nulls=True)

    for chunk in chunk_docs:
        content = chunk.page_content.strip()
        if not content:
            continue

        rows.append(
            build_chunk_row_from_doc(
                document_id=document_id,
                document_pk=document_pk,
                chunk=chunk,
            )
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
) -> list[tuple[Chunk, float]]:
    terms = [term.strip() for term in query_terms if term and term.strip()]
    if not terms:
        return []

    document_table = Document.__table__
    score_expr = literal(0.0)
    conditions = []
    for term in terms:
        content_match = Chunk.content.ilike(f"%{term}%")
        title_match = Chunk.section_title.ilike(f"%{term}%")
        path_match = Chunk.section_path.ilike(f"%{term}%")
        summary_match = Chunk.section_summary.ilike(f"%{term}%")
        conditions.extend([content_match, title_match, path_match, summary_match])
        score_expr += case((content_match, 1.0), else_=0.0)
        score_expr += case((title_match, 0.9), else_=0.0)
        score_expr += case((path_match, 0.7), else_=0.0)
        score_expr += case((summary_match, 0.6), else_=0.0)

    score_label = score_expr.label("keyword_score")
    sql = select(Chunk, score_label).join(document_table, Chunk.document_pk == document_table.c.pk).where(
        document_table.c.knowledge_base_id == knowledge_base_id,
        or_(*conditions),
    )
    if user_id is not None:
        sql = sql.where(document_table.c.user_id == user_id)

    sql = sql.order_by(score_label.desc(), Chunk.document_pk.asc(), Chunk.chunk_index.asc()).limit(limit)
    res = await db.execute(sql)
    return [(row[0], float(row[1] or 0.0)) for row in res.all()]


def build_chunk_row_from_doc(
    *,
    document_id: str,
    document_pk: int,
    chunk: LCDocument,
) -> dict[str, object]:
    content = chunk.page_content.strip()
    start_offset = chunk.metadata.get("start_offset")
    end_offset = start_offset + len(content) if isinstance(start_offset, int) else None

    return {
        "id": chunk.metadata["chunk_id"],
        "document_id": document_id,
        "document_pk": document_pk,
        "chunk_index": chunk.metadata["chunk_index"],
        "content": content,
        "page_no": chunk.metadata.get("page_no"),
        "start_offset": start_offset,
        "end_offset": end_offset,
        "section_id": chunk.metadata.get("section_id"),
        "section_title": chunk.metadata.get("section_title"),
        "section_level": chunk.metadata.get("section_level"),
        "section_path": chunk.metadata.get("section_path"),
        "section_summary": chunk.metadata.get("section_summary"),
        "section_chunk_index": chunk.metadata.get("section_chunk_index"),
    }
