import hashlib
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.crud.chunk import list_chunks_by_document_id
from app.mneme.models.document import Document
from app.mneme.models.memory_entry import MemoryEntry
from app.mneme.schemas.memory_agent import (
    DocumentChunkPayload,
    DocumentMemoryObservedPayload,
    DocumentProjectionPayload,
    MemoryAgentEvent,
)


def _section_path_parts(section_path: str | None) -> list[str]:
    if not section_path:
        return []
    return [part.strip() for part in section_path.split(">") if part.strip()]


def _projection_id(*, document: Document, aggregate_hash: str) -> str:
    identity = (
        f"{document.user_id}{document.knowledge_base_id}{document.id}"
        f"{document.updated_at.isoformat()}{aggregate_hash}"
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def build_document_memory_observed_event(
    *,
    document: Document,
    projection_id: str,
    document_version: str,
    chunk_id: str,
    chunk_content: str,
    excerpt: str,
    observed_at: datetime,
) -> MemoryAgentEvent:
    bounded_excerpt = excerpt[:20_000]
    if not bounded_excerpt or bounded_excerpt not in chunk_content:
        raise ValueError("document memory excerpt must occur in its projection chunk")
    content_hash = hashlib.sha256(chunk_content.encode("utf-8")).hexdigest()
    excerpt_hash = hashlib.sha256(bounded_excerpt.encode("utf-8")).hexdigest()
    identity = "\0".join(
        (
            str(document.user_id),
            document.knowledge_base_id,
            document.id,
            projection_id,
            chunk_id,
            document_version,
            content_hash,
            excerpt_hash,
        )
    )
    event_id = f"document-memory:{hashlib.sha256(identity.encode('utf-8')).hexdigest()}"
    return MemoryAgentEvent(
        event_id=event_id,
        event_type="document.memory.observed",
        occurred_at=observed_at,
        owner_id=document.user_id,
        knowledge_base_id=document.knowledge_base_id,
        payload=DocumentMemoryObservedPayload(
            document_id=document.id,
            projection_id=projection_id,
            chunk_id=chunk_id,
            document_version=document_version,
            content_hash=content_hash,
            excerpt_hash=excerpt_hash,
            observed_at=observed_at,
            excerpt=bounded_excerpt,
        ).model_dump(mode="json"),
    )


def build_document_memory_observation_events(
    *,
    document: Document,
    projection_events: list[MemoryAgentEvent],
) -> list[MemoryAgentEvent]:
    projection_payloads = [
        DocumentProjectionPayload.model_validate(event.payload)
        for event in projection_events
    ]
    if not projection_payloads:
        raise ValueError("document memory observations require projection batches")
    first = projection_payloads[0]
    if (
        first.document_id != document.id
        or first.document_version != document.updated_at.isoformat()
    ):
        raise ValueError("document projection identity is not current")
    if any(
        payload.projection_id != first.projection_id
        or payload.document_id != first.document_id
        or payload.document_version != first.document_version
        for payload in projection_payloads
    ):
        raise ValueError("document projection batches do not share one identity")
    chunks = sorted(
        [chunk for payload in projection_payloads for chunk in payload.chunks],
        key=lambda chunk: (chunk.chunk_index, chunk.chunk_id),
    )
    return [
        build_document_memory_observed_event(
            document=document,
            projection_id=first.projection_id,
            document_version=first.document_version,
            chunk_id=chunk.chunk_id,
            chunk_content=chunk.content,
            excerpt=chunk.content,
            observed_at=document.updated_at,
        )
        for chunk in chunks
    ]


def build_legacy_document_memory_observed_event(
    *,
    document: Document,
    memory: MemoryEntry,
    projection_events: list[MemoryAgentEvent],
) -> MemoryAgentEvent:
    if memory.document_id != document.id or memory.user_id != document.user_id:
        raise ValueError("legacy memory is outside its document owner scope")
    if memory.knowledge_base_id != document.knowledge_base_id:
        raise ValueError("legacy memory is outside its document knowledge-base scope")
    projection_payloads = [
        DocumentProjectionPayload.model_validate(event.payload)
        for event in projection_events
    ]
    matching_chunks = [
        chunk
        for payload in projection_payloads
        for chunk in payload.chunks
        if chunk.chunk_id == memory.chunk_id
    ]
    if len(matching_chunks) != 1 or not projection_payloads:
        raise ValueError("legacy memory chunk is missing or duplicated in its projection")
    first = projection_payloads[0]
    if (
        first.document_id != document.id
        or first.document_version != document.updated_at.isoformat()
        or any(
            payload.projection_id != first.projection_id
            or payload.document_id != first.document_id
            or payload.document_version != first.document_version
            for payload in projection_payloads
        )
    ):
        raise ValueError("legacy memory projection identity is not current")
    return build_document_memory_observed_event(
        document=document,
        projection_id=first.projection_id,
        document_version=first.document_version,
        chunk_id=memory.chunk_id,
        chunk_content=matching_chunks[0].content,
        excerpt=memory.evidence_text,
        observed_at=memory.first_seen_at,
    )


async def build_document_projection_batches(
    db: AsyncSession,
    *,
    document: Document,
    batch_size: int = 50,
) -> list[MemoryAgentEvent]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    if not document.knowledge_base_id:
        raise ValueError("document projection requires a knowledge_base_id")

    chunks = sorted(
        await list_chunks_by_document_id(db, document_id=document.id),
        key=lambda chunk: (chunk.chunk_index, chunk.id),
    )
    chunk_indexes = [chunk.chunk_index for chunk in chunks]
    if chunk_indexes != list(range(len(chunks))):
        raise ValueError("document chunk indexes must be contiguous from zero")
    if not chunks:
        raise ValueError("document projection requires at least one chunk")

    chunk_payloads = [
        DocumentChunkPayload(
            chunk_id=chunk.id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            content_hash=hashlib.sha256(chunk.content.encode("utf-8")).hexdigest(),
            page_no=chunk.page_no,
            section_path=_section_path_parts(chunk.section_path),
        )
        for chunk in chunks
    ]
    aggregate_hash = hashlib.sha256(
        "".join(chunk.content_hash for chunk in chunk_payloads).encode("ascii")
    ).hexdigest()
    projection_id = _projection_id(document=document, aggregate_hash=aggregate_hash)
    document_version = document.updated_at.isoformat()
    occurred_at: datetime = document.updated_at
    batch_count = (len(chunk_payloads) + batch_size - 1) // batch_size

    return [
        MemoryAgentEvent(
            event_id=f"projection:{projection_id}:{batch_index}",
            event_type="document.projection.upserted",
            occurred_at=occurred_at,
            owner_id=document.user_id,
            knowledge_base_id=document.knowledge_base_id,
            payload=DocumentProjectionPayload(
                projection_id=projection_id,
                document_id=document.id,
                document_version=document_version,
                file_name=document.file_name,
                batch_index=batch_index,
                batch_count=batch_count,
                aggregate_hash=aggregate_hash,
                chunks=chunk_payloads[batch_index * batch_size:(batch_index + 1) * batch_size],
            ).model_dump(mode="json"),
        )
        for batch_index in range(batch_count)
    ]
