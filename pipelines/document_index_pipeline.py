from collections.abc import Awaitable, Callable

from conf.config import settings
from conf.database import open_write_session
from conf.logging import log_event
from clients.document_loader_client import load_langchain_documents
from clients.text_splitter_client import split_documents
from clients.vector_store_client import add_documents_to_vector_store_in_batches
from crud.chunk import create_chunks
from crud.document import update_document_status
from models.document import Document
from schemas.document import DocumentIndexPipelineResult
from services.graph_projection_service import sync_document_projection_from_db
from services.memory_service import rebuild_memory_entries_for_document


async def emit_stage(
    stage: str,
    *,
    on_stage_change: Callable[[str], Awaitable[None]] | None,
) -> None:
    log_event("document_pipeline", "debug", "document_index.stage_change", stage=stage)
    if on_stage_change:
        await on_stage_change(stage)


async def update_document_status_with_projection(
    *,
    document_id: str,
    status: str,
) -> Document | None:
    async with open_write_session() as db:
        document = await update_document_status(
            db,
            document_id=document_id,
            status=status,
        )
        if document:
            await sync_document_projection_from_db(
                db,
                document=document,
            )
        return document


async def persist_chunks_for_document(
    *,
    document_id: str,
    document_pk: int,
    chunk_docs: list,
) -> None:
    async with open_write_session() as db:
        await create_chunks(
            db,
            document_id=document_id,
            document_pk=document_pk,
            chunk_docs=chunk_docs,
        )


async def run_document_index_pipeline(
    *,
    document: Document,
    on_stage_change: Callable[[str], Awaitable[None]] | None = None,
) -> DocumentIndexPipelineResult:
    indexed_document = await update_document_status_with_projection(
        document_id=document.id,
        status="indexing",
    )
    doc = indexed_document or document

    log_event(
        "document_pipeline",
        "info",
        "document_index.start",
        document_id=doc.id,
        knowledge_base_id=doc.knowledge_base_id,
    )

    await emit_stage("parsing", on_stage_change=on_stage_change)
    docs = await load_langchain_documents(
        file_path=doc.file_path,
        file_type=doc.file_type,
        user_id=doc.user_id,
        knowledge_base_id=doc.knowledge_base_id,
        knowledge_base_pk=doc.knowledge_base_pk,
        file_name=doc.file_name,
        document_id=doc.id,
        document_pk=doc.pk,
    )
    log_event(
        "document_pipeline",
        "info",
        "document_index.parsed",
        document_id=doc.id,
        parsed_doc_count=len(docs),
    )

    await emit_stage("chunking", on_stage_change=on_stage_change)
    chunk_docs = await split_documents(document_id=doc.id, documents=docs)
    section_count = len(
        {
            chunk.metadata.get("section_id")
            for chunk in chunk_docs
            if chunk.metadata.get("section_id")
        }
    )
    log_event(
        "document_pipeline",
        "info",
        "document_index.chunked",
        document_id=doc.id,
        chunk_count=len(chunk_docs),
        section_count=section_count,
    )

    await persist_chunks_for_document(
        document_id=doc.id,
        document_pk=doc.pk,
        chunk_docs=chunk_docs,
    )

    await emit_stage("memory_extracting", on_stage_change=on_stage_change)
    memory_result = await rebuild_memory_entries_for_document(document=doc)

    await emit_stage("embedding", on_stage_change=on_stage_change)
    await emit_stage("vector_upserting", on_stage_change=on_stage_change)
    vector_result = await add_documents_to_vector_store_in_batches(
        chunk_docs=chunk_docs,
        batch_size=settings.INDEX_VECTOR_BATCH_SIZE,
    )
    log_event(
        "document_pipeline",
        "info",
        "document_index.vector_upsert_completed",
        document_id=doc.id,
        batch_count=vector_result["batch_count"],
        batch_size=vector_result["batch_size"],
        indexed_vector_count=vector_result["total_count"],
    )

    final_document = await update_document_status_with_projection(
        document_id=doc.id,
        status="indexed",
    )
    if final_document:
        doc = final_document

    log_event(
        "document_pipeline",
        "info",
        "document_index.completed",
        document_id=doc.id,
        status="indexed",
        section_count=section_count,
    )

    return DocumentIndexPipelineResult(
        document_id=doc.id,
        knowledge_base_id=doc.knowledge_base_id,
        chunk_count=len(chunk_docs),
        section_count=section_count,
        deleted_memory_entry_count=memory_result["deleted_entry_count"],
        memory_entry_count=memory_result["entry_count"],
        vector_batch_count=vector_result["batch_count"],
        vector_batch_size=vector_result["batch_size"],
        indexed_vector_count=vector_result["total_count"],
        status="indexed",
    )
