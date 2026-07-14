from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.clients.vector_store_client import delete_documents_from_vector_store
from app.mneme.conf.config import settings
from app.mneme.crud.chunk import delete_chunks_by_document_id, list_chunks_by_document_id
from app.mneme.crud.document import delete_document_by_id, list_documents
from app.mneme.crud.knowledge_base import delete_knowledge_base_by_id, get_knowledge_base_by_id
from app.mneme.crud.memory_entry import delete_memory_entries_by_document_id, delete_memory_entries_by_knowledge_base_id
from app.mneme.crud.task_record import delete_task_records_by_target_id
from app.mneme.domains.graph.projection import delete_document_projection, delete_knowledge_base_projection
from app.mneme.domains.memory.projection import rebuild_memory_governance_projection
from app.mneme.domains.tasks.outbox import enqueue_document_deleted, enqueue_knowledge_base_deleted
from app.mneme.models.document import Document


async def delete_document_resources(
        db: AsyncSession,
        *,
        document: Document,
        rebuild_memory_projection: bool = True,
) -> dict[str, int | str]:
    chunk_rows = await list_chunks_by_document_id(
        db,
        document_id=document.id,
    )
    chunk_ids = [chunk.id for chunk in chunk_rows]

    if settings.MEMORY_AGENT_ENABLED:
        deleted_vector_count = 0
    else:
        await delete_documents_from_vector_store(ids=chunk_ids)
        deleted_vector_count = len(chunk_ids)
    deleted_memory_entry_count = await delete_memory_entries_by_document_id(
        db,
        document_id=document.id,
    )
    if rebuild_memory_projection:
        await rebuild_memory_governance_projection(
            db,
            user_id=document.user_id,
            knowledge_base_id=document.knowledge_base_id,
            knowledge_base_pk=document.knowledge_base_pk,
        )
    deleted_chunk_count = await delete_chunks_by_document_id(
        db,
        document_id=document.id,
    )
    deleted_task_count = await delete_task_records_by_target_id(
        db,
        target_id=document.id,
        task_type="document_index",
    )
    if settings.MEMORY_AGENT_ENABLED:
        await enqueue_document_deleted(
            db,
            owner_id=document.user_id,
            knowledge_base_id=document.knowledge_base_id,
            document_id=document.id,
            source_version=document.updated_at,
        )
    await delete_document_by_id(
        db,
        document_id=document.id,
    )

    file_path = Path(document.file_path)
    if file_path.exists():
        file_path.unlink()

    if not settings.MEMORY_AGENT_ENABLED:
        await delete_document_projection(document_id=document.id)

    return {
        "document_id": document.id,
        "knowledge_base_id": document.knowledge_base_id,
        "chunk_count": deleted_chunk_count,
        "deleted_memory_entry_count": deleted_memory_entry_count,
        "deleted_task_count": deleted_task_count,
        "deleted_vector_count": deleted_vector_count,
    }


async def delete_knowledge_base_resources(
        db: AsyncSession,
        *,
        knowledge_base_id: str,
        knowledge_base_pk: int,
) -> dict[str, int | str]:
    knowledge_base = None
    if settings.MEMORY_AGENT_ENABLED:
        knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id)
        if knowledge_base is None:
            raise ValueError("knowledge base must exist before deleting its resources")

    documents = await list_documents(
        db,
        knowledge_base_pk=knowledge_base_pk,
    )

    total_chunk_count = 0
    total_deleted_memory_entry_count = 0
    total_deleted_task_count = 0
    total_deleted_vector_count = 0

    for document in documents:
        result = await delete_document_resources(
            db,
            document=document,
            rebuild_memory_projection=False,
        )
        total_chunk_count += int(result["chunk_count"])
        total_deleted_memory_entry_count += int(result["deleted_memory_entry_count"])
        total_deleted_task_count += int(result["deleted_task_count"])
        total_deleted_vector_count += int(result["deleted_vector_count"])

    total_deleted_memory_entry_count += await delete_memory_entries_by_knowledge_base_id(
        db,
        knowledge_base_id=knowledge_base_id,
    )
    if knowledge_base is not None:
        await enqueue_knowledge_base_deleted(
            db,
            owner_id=knowledge_base.user_id,
            knowledge_base_id=knowledge_base.id,
            source_version=knowledge_base.updated_at,
        )
    await delete_knowledge_base_by_id(
        db,
        knowledge_base_id=knowledge_base_id,
    )
    if not settings.MEMORY_AGENT_ENABLED:
        await delete_knowledge_base_projection(knowledge_base_id=knowledge_base_id)

    return {
        "knowledge_base_id": knowledge_base_id,
        "document_count": len(documents),
        "chunk_count": total_chunk_count,
        "deleted_memory_entry_count": total_deleted_memory_entry_count,
        "deleted_task_count": total_deleted_task_count,
        "deleted_vector_count": total_deleted_vector_count,
    }
