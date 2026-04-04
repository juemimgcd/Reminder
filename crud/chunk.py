from langchain_core.documents import Document as LCDocument
from sqlalchemy.ext.asyncio import AsyncSession

from models.chunk import Chunk


async def create_chunks(
        db: AsyncSession,
        *,
        document_id: str,
        chunk_docs: list[LCDocument],
) -> list[Chunk]:

    chunks = []

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


        chunk_obj = Chunk(
            id=chunk.metadata["chunk_id"],
            document_id=document_id,
            chunk_index=chunk.metadata["chunk_index"],
            page_no=chunk.metadata["page_no"],
            start_offset=start_offset,
            end_offset=end_offset
        )
        chunks.append(chunk_obj)

    db.add_all(chunks)
    await db.refresh(chunks)

    return chunks










