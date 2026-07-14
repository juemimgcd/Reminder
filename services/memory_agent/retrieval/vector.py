from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory_agent.models.document_chunk import DocumentChunk
from services.memory_agent.models.document_projection import DocumentProjection
from services.memory_agent.retrieval.contracts import DocumentSearchHit, RetrievalScope
from services.memory_agent.services.embeddings import embed_texts


async def search_vector(
    db: AsyncSession,
    *,
    scope: RetrievalScope,
    query: str,
    limit: int,
) -> list[DocumentSearchHit]:
    if limit <= 0:
        return []

    query_embedding = (await embed_texts([query]))[0]
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
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
        )
        .order_by(distance.asc(), DocumentChunk.chunk_id.asc())
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
