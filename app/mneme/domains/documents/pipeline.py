from collections.abc import Awaitable, Callable
from datetime import datetime

from app.mneme.clients.document_loader_client import load_langchain_documents
from app.mneme.clients.text_splitter_client import split_documents
from app.mneme.conf.config import settings
from app.mneme.conf.database import open_write_session
from app.mneme.conf.logging import log_event
from app.mneme.crud.chunk import create_chunks
from app.mneme.crud.document import update_document_status
from app.mneme.domains.documents.agent_projection import (
    build_document_memory_observation_events,
    build_document_projection_batches,
)
from app.mneme.domains.memory.service import rebuild_memory_entries_for_document
from app.mneme.domains.tasks.outbox import (
    enqueue_document_agent_projection,
    enqueue_document_graph_sync_event,
    enqueue_document_memory_observed,
    enqueue_document_vector_reindex_event,
    process_outbox_event_by_id,
)
from app.mneme.models.document import Document
from app.mneme.schemas.document import DocumentIndexPipelineResult


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
    enqueue_projection: bool = False,
) -> Document | None:
    async with open_write_session() as db:
        document = await update_document_status(
            db,
            document_id=document_id,
            status=status,
        )
    if document and enqueue_projection:
        event = await enqueue_document_graph_sync_event(
            document_id=document.id,
            operation_id=f"document-status-{status}-{document.updated_at.isoformat()}",
        )
        await process_outbox_event_by_id(event_id=event.id)
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
        enqueue_projection=False,
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
    if settings.MEMORY_AGENT_ENABLED:
        memory_result = {"deleted_entry_count": 0, "entry_count": 0}
    else:
        memory_result = await rebuild_memory_entries_for_document(document=doc)

    await emit_stage("embedding", on_stage_change=on_stage_change)
    await emit_stage("vector_upserting", on_stage_change=on_stage_change)
    if settings.MEMORY_AGENT_ENABLED:
        async with open_write_session() as db:
            final_document = await update_document_status(
                db,
                document_id=doc.id,
                status="indexed",
            )
            if final_document is None:
                raise RuntimeError("document disappeared before projection enqueue")
            doc = final_document
            projection_batches = await build_document_projection_batches(
                db,
                document=doc,
            )
            for event in projection_batches:
                await enqueue_document_agent_projection(db, event=event)
            memory_observations = build_document_memory_observation_events(
                document=doc,
                projection_events=projection_batches,
            )
            for event in memory_observations:
                await enqueue_document_memory_observed(db, event=event)
        vector_result = {
            "batch_count": len(projection_batches),
            "batch_size": 50,
            "total_count": len(chunk_docs),
        }
    else:
        vector_event = await enqueue_document_vector_reindex_event(
            document_id=doc.id,
            operation_id=f"document-index-{doc.id}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            delete_existing=True,
        )
        vector_outbox_result = await process_outbox_event_by_id(event_id=vector_event.id)
        vector_result = vector_outbox_result["result"]
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
            enqueue_projection=True,
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
