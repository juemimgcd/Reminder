from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.memoria.server.models.document_chunk import DocumentChunk
from app.mneme.memoria.server.models.document_projection import DocumentProjection
from app.mneme.memoria.server.retrieval.contracts import DocumentSearchHit, RetrievalScope


async def search_keyword(
    db: AsyncSession,
    *,
    scope: RetrievalScope,
    query: str,
    limit: int,
) -> list[DocumentSearchHit]:
    if limit <= 0:
        return []

    text_query = func.websearch_to_tsquery(literal_column("'simple'::regconfig"), query)
    rank = func.ts_rank_cd(DocumentChunk.search_vector, text_query)
    statement = (
        select(
            DocumentChunk.chunk_id,
            DocumentChunk.document_id,
            DocumentChunk.document_version,
            DocumentChunk.chunk_index,
            DocumentChunk.content,
            DocumentChunk.page_no,
            DocumentChunk.section_path,
            DocumentProjection.file_name,
        )
        .join(
            DocumentProjection,
            DocumentProjection.projection_id == DocumentChunk.projection_id,
        )
        .where(
            DocumentChunk.owner_id == scope.owner_id,
            DocumentChunk.knowledge_base_id == scope.knowledge_base_id,
            DocumentChunk.is_active.is_(True),
            DocumentProjection.owner_id == scope.owner_id,
            DocumentProjection.knowledge_base_id == scope.knowledge_base_id,
            DocumentProjection.status == "active",
            DocumentChunk.search_vector.op("@@")(text_query),
        )
        .order_by(rank.desc(), DocumentChunk.chunk_id.asc())
        .limit(limit)
    )
    rows = (await db.execute(statement)).mappings().all()
    return [
        DocumentSearchHit(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            content=row["content"],
            metadata={
                "document_version": row["document_version"],
                "file_name": row["file_name"],
                "chunk_index": row["chunk_index"],
                "page_no": row["page_no"],
                "section_path": row["section_path"],
            },
        )
        for row in rows
    ]
