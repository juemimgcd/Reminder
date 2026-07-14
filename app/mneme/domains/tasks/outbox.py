import hashlib
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from langchain_core.documents import Document as LCDocument
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.clients.memory_agent_client import MemoryAgentRetryable
from app.mneme.clients.vector_store_client import (
    add_documents_to_vector_store_in_batches,
    delete_documents_from_vector_store,
)
from app.mneme.conf.config import settings
from app.mneme.conf.database import open_read_session, open_write_session
from app.mneme.conf.logging import app_logger
from app.mneme.crud.chunk import list_chunks_by_document_id
from app.mneme.crud.document import get_document_by_id
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id
from app.mneme.crud.memory_entry import list_memory_entries_by_document_id
from app.mneme.crud.outbox_event import (
    get_outbox_event_by_id,
    list_dispatchable_outbox_events,
    update_outbox_event_status,
)
from app.mneme.crud.user import get_user_by_id
from app.mneme.domains.graph.projection import sync_document_memory_projection
from app.mneme.domains.tasks.outbox_http import apply_memory_agent_http_event
from app.mneme.models.chunk import Chunk
from app.mneme.models.document import Document
from app.mneme.models.outbox_event import OutboxEvent
from app.mneme.schemas.memory_agent import MemoryAgentEvent
from app.mneme.utils.exceptions import BusinessException

OUTBOX_PENDING = "pending"
OUTBOX_RUNNING = "running"
OUTBOX_SUCCEEDED = "succeeded"
OUTBOX_FAILED = "failed"
OUTBOX_DEAD_LETTER = "dead_letter"

EVENT_DOCUMENT_VECTOR_REINDEX = "document.vector.reindex"
EVENT_DOCUMENT_GRAPH_SYNC = "document.graph.sync"

BACKEND_MILVUS = "milvus"
BACKEND_NEO4J = "neo4j"
MAX_MEMORY_AGENT_ERROR_LENGTH = 2000

_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(
        r"(?:\b(?:password|passwd|pwd|api[\s_-]?key|access[\s_-]?token|token|secret|"
        r"refresh[\s_-]?token|auth[\s_-]?token|client[\s_-]?secret|private[\s_-]?key)\b|"
        r"(?:密码|密钥|令牌|口令))\s*(?:is|是|为|:|=)\s*"
        r"[\"']?[^\s,;\"']{4,}",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://[^\s:/]+:[^\s@]+@", re.IGNORECASE),
)


def build_outbox_event_id() -> str:
    return f"outbox_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _contains_secret(text: str) -> bool:
    return any(pattern.search(text) is not None for pattern in _SECRET_PATTERNS)


def build_outbox_idempotency_key(
        *,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        operation_id: str,
) -> str:
    return f"{event_type}:{aggregate_type}:{aggregate_id}:{operation_id}"


def calculate_next_attempt_at(*, attempt_count: int) -> datetime:
    delay_seconds = settings.OUTBOX_RETRY_BASE_DELAY_SECONDS * max(1, attempt_count)
    return datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)


def should_dead_letter(*, attempt_count: int, max_attempts: int) -> bool:
    return attempt_count >= max_attempts


def build_chunk_document(document: Document, chunk: Chunk) -> LCDocument:
    return LCDocument(
        page_content=chunk.content,
        metadata={
            "user_id": document.user_id,
            "knowledge_base_id": document.knowledge_base_id,
            "knowledge_base_pk": document.knowledge_base_pk,
            "document_id": document.id,
            "document_pk": document.pk,
            "file_name": document.file_name,
            "file_type": document.file_type,
            "source": document.file_path,
            "chunk_id": chunk.id,
            "chunk_index": chunk.chunk_index,
            "page_no": chunk.page_no,
            "start_offset": chunk.start_offset,
            "end_offset": chunk.end_offset,
            "section_id": chunk.section_id,
            "section_title": chunk.section_title,
            "section_level": chunk.section_level,
            "section_path": chunk.section_path,
            "section_summary": chunk.section_summary,
            "section_chunk_index": chunk.section_chunk_index,
        },
    )


async def enqueue_outbox_event(
        *,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        target_backend: str,
        payload: dict[str, Any],
        operation_id: str,
        db: AsyncSession | None = None,
) -> OutboxEvent:
    """Create an Outbox row without taking ownership of a supplied session."""
    idempotency_key = build_outbox_idempotency_key(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        operation_id=operation_id,
    )
    if db is not None:
        return await _create_outbox_event_if_missing(
            db,
            idempotency_key=idempotency_key,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            target_backend=target_backend,
            payload=payload,
        )

    async with open_write_session() as managed_db:
        return await _create_outbox_event_if_missing(
            managed_db,
            idempotency_key=idempotency_key,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            target_backend=target_backend,
            payload=payload,
        )


async def _create_outbox_event_if_missing(
        db: AsyncSession,
        *,
        idempotency_key: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        target_backend: str,
        payload: dict[str, Any],
) -> OutboxEvent:
    result = await db.execute(
        insert(OutboxEvent)
        .values(
            id=build_outbox_event_id(),
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            target_backend=target_backend,
            payload=payload,
            idempotency_key=idempotency_key,
            max_attempts=settings.OUTBOX_EVENT_MAX_ATTEMPTS,
        )
        .on_conflict_do_nothing(index_elements=[OutboxEvent.idempotency_key])
        .returning(OutboxEvent)
    )
    inserted = result.scalar_one_or_none()
    if inserted is not None:
        return inserted

    existing = await db.scalar(
        select(OutboxEvent).where(OutboxEvent.idempotency_key == idempotency_key)
    )
    if existing is None:
        raise RuntimeError("outbox idempotency conflict row could not be loaded")
    return existing


async def enqueue_document_vector_reindex_event(
        *,
        document_id: str,
        operation_id: str,
        delete_existing: bool = True,
) -> OutboxEvent:
    return await enqueue_outbox_event(
        event_type=EVENT_DOCUMENT_VECTOR_REINDEX,
        aggregate_type="document",
        aggregate_id=document_id,
        target_backend=BACKEND_MILVUS,
        payload={
            "document_id": document_id,
            "delete_existing": delete_existing,
        },
        operation_id=operation_id,
    )


async def enqueue_document_graph_sync_event(
        *,
        document_id: str,
        operation_id: str,
) -> OutboxEvent:
    return await enqueue_outbox_event(
        event_type=EVENT_DOCUMENT_GRAPH_SYNC,
        aggregate_type="document",
        aggregate_id=document_id,
        target_backend=BACKEND_NEO4J,
        payload={
            "document_id": document_id,
        },
        operation_id=operation_id,
    )


async def mark_outbox_running(*, event: OutboxEvent) -> None:
    async with open_write_session() as db:
        await update_outbox_event_status(
            db,
            event_id=event.id,
            status=OUTBOX_RUNNING,
            attempt_count=event.attempt_count + 1,
            locked_at=datetime.now(timezone.utc),
            clear_error=True,
        )


async def mark_outbox_succeeded(*, event_id: str) -> None:
    async with open_write_session() as db:
        await update_outbox_event_status(
            db,
            event_id=event_id,
            status=OUTBOX_SUCCEEDED,
            processed_at=datetime.now(timezone.utc),
            clear_error=True,
        )


async def mark_outbox_failed(*, event: OutboxEvent, exc: Exception) -> None:
    next_attempt_count = event.attempt_count + 1
    attempts_exhausted = should_dead_letter(
        attempt_count=next_attempt_count,
        max_attempts=event.max_attempts,
    )
    if event.target_backend == settings.MEMORY_AGENT_OUTBOX_TARGET:
        status = (
            OUTBOX_FAILED
            if isinstance(exc, MemoryAgentRetryable) and not attempts_exhausted
            else OUTBOX_DEAD_LETTER
        )
    else:
        status = OUTBOX_DEAD_LETTER if attempts_exhausted else OUTBOX_FAILED
    async with open_write_session() as db:
        await update_outbox_event_status(
            db,
            event_id=event.id,
            status=status,
            attempt_count=next_attempt_count,
            next_attempt_at=None if status == OUTBOX_DEAD_LETTER else calculate_next_attempt_at(
                attempt_count=next_attempt_count,
            ),
            last_error=_bounded_error_detail(event=event, exc=exc),
        )


async def _enqueue_memory_agent_event(
        db: AsyncSession,
        *,
        event: MemoryAgentEvent,
        aggregate_type: str,
        aggregate_id: str,
) -> OutboxEvent:
    return await enqueue_outbox_event(
        db=db,
        event_type=event.event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        target_backend=settings.MEMORY_AGENT_OUTBOX_TARGET,
        payload=event.model_dump(mode="json"),
        operation_id=event.event_id,
    )


async def enqueue_document_agent_projection(
        db: AsyncSession,
        *,
        event: MemoryAgentEvent,
) -> OutboxEvent:
    if event.event_type != "document.projection.upserted":
        raise ValueError("document projection enqueue requires a projection event")
    document_id = str(event.payload["document_id"])
    return await _enqueue_memory_agent_event(
        db,
        event=event,
        aggregate_type="document",
        aggregate_id=document_id,
    )


def _memory_event_id(prefix: str, *identity_parts: str) -> str:
    identity = "\0".join(identity_parts)
    return f"{prefix}:{hashlib.sha256(identity.encode('utf-8')).hexdigest()}"


async def enqueue_conversation_completed(
    db: AsyncSession,
    *,
    owner_id: int,
    knowledge_base_id: str,
    session_id: str,
    user_message_id: str,
    user_content: str,
    user_created_at: datetime,
    assistant_message_id: str,
    assistant_content: str,
    assistant_created_at: datetime,
) -> OutboxEvent | None:
    if _contains_secret(user_content) or _contains_secret(assistant_content):
        return None
    event = MemoryAgentEvent(
        event_id=_memory_event_id(
            "conversation-completed",
            str(owner_id),
            session_id,
            user_message_id,
            assistant_message_id,
        ),
        event_type="conversation.completed",
        occurred_at=assistant_created_at,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        payload={
            "session_id": session_id,
            "user_message": {
                "id": user_message_id,
                "content": user_content[:20_000],
                "created_at": user_created_at.isoformat(),
            },
            "assistant_message": {
                "id": assistant_message_id,
                "content": assistant_content[:20_000],
                "created_at": assistant_created_at.isoformat(),
            },
        },
    )
    return await _enqueue_memory_agent_event(
        db,
        event=event,
        aggregate_type="conversation",
        aggregate_id=session_id,
    )


async def enqueue_user_memory_requested(
    db: AsyncSession,
    *,
    owner_id: int,
    knowledge_base_id: str,
    session_id: str,
    message_id: str,
    excerpt: str,
    message_created_at: datetime,
) -> OutboxEvent | None:
    if _contains_secret(excerpt):
        return None
    event = MemoryAgentEvent(
        event_id=_memory_event_id(
            "memory-requested",
            str(owner_id),
            session_id,
            message_id,
            message_created_at.isoformat(),
        ),
        event_type="user.memory_requested",
        occurred_at=message_created_at,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        payload={
            "session_id": session_id,
            "message_id": message_id,
            "message_created_at": message_created_at.isoformat(),
            "excerpt": excerpt[:20_000],
        },
    )
    return await _enqueue_memory_agent_event(
        db,
        event=event,
        aggregate_type="chat_message",
        aggregate_id=message_id,
    )


async def enqueue_document_deleted(
        db: AsyncSession,
        *,
        owner_id: int,
        knowledge_base_id: str,
        document_id: str,
        source_version: datetime,
) -> OutboxEvent:
    source_version_text = source_version.isoformat()
    event = MemoryAgentEvent(
        event_id=_deletion_event_id(
            "document-deleted",
            str(owner_id),
            knowledge_base_id,
            document_id,
            source_version_text,
        ),
        event_type="document.deleted",
        occurred_at=source_version,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        payload={
            "owner_id": owner_id,
            "knowledge_base_id": knowledge_base_id,
            "document_id": document_id,
            "source_version": source_version_text,
        },
    )
    return await _enqueue_memory_agent_event(
        db,
        event=event,
        aggregate_type="document",
        aggregate_id=document_id,
    )


async def enqueue_knowledge_base_deleted(
        db: AsyncSession,
        *,
        owner_id: int,
        knowledge_base_id: str,
        source_version: datetime,
) -> OutboxEvent:
    source_version_text = source_version.isoformat()
    event = MemoryAgentEvent(
        event_id=_deletion_event_id(
            "knowledge-base-deleted",
            str(owner_id),
            knowledge_base_id,
            source_version_text,
        ),
        event_type="knowledge_base.deleted",
        occurred_at=source_version,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        payload={
            "owner_id": owner_id,
            "knowledge_base_id": knowledge_base_id,
            "source_version": source_version_text,
        },
    )
    return await _enqueue_memory_agent_event(
        db,
        event=event,
        aggregate_type="knowledge_base",
        aggregate_id=knowledge_base_id,
    )


def _deletion_event_id(prefix: str, *identity_parts: str) -> str:
    return _memory_event_id(prefix, *identity_parts)


def _bounded_error_detail(*, event: OutboxEvent, exc: Exception) -> str:
    if event.target_backend == settings.MEMORY_AGENT_OUTBOX_TARGET:
        detail = exc.message if isinstance(exc, BusinessException) else "memory agent delivery failed"
        return detail[:MAX_MEMORY_AGENT_ERROR_LENGTH]
    return str(exc)


async def load_outbox_event_snapshot(*, event_id: str) -> OutboxEvent | None:
    async with open_read_session() as db:
        return await get_outbox_event_by_id(db, event_id=event_id)


async def apply_vector_reindex_event(event: OutboxEvent) -> dict[str, int | str]:
    document_id = event.payload.get("document_id")
    if not document_id:
        raise BusinessException(message="outbox vector event missing document_id", code=5017, status_code=500)

    async with open_read_session() as db:
        document = await get_document_by_id(db, document_id=document_id)
        if not document:
            raise BusinessException(message="document not found for vector outbox event", code=4044, status_code=404)
        chunks = await list_chunks_by_document_id(db, document_id=document.id)
        chunk_docs = [build_chunk_document(document, chunk) for chunk in chunks]

    if event.payload.get("delete_existing", True):
        await delete_documents_from_vector_store(
            ids=[str(doc.metadata["chunk_id"]) for doc in chunk_docs],
        )

    vector_result = await add_documents_to_vector_store_in_batches(
        chunk_docs=chunk_docs,
        batch_size=settings.INDEX_VECTOR_BATCH_SIZE,
    )
    return {
        "document_id": document_id,
        "total_count": vector_result["total_count"],
        "batch_count": vector_result["batch_count"],
        "batch_size": vector_result["batch_size"],
        "indexed_vector_count": vector_result["total_count"],
        "vector_batch_count": vector_result["batch_count"],
        "vector_batch_size": vector_result["batch_size"],
    }


async def apply_graph_sync_event(event: OutboxEvent) -> dict[str, int | str]:
    document_id = event.payload.get("document_id")
    if not document_id:
        raise BusinessException(message="outbox graph event missing document_id", code=5018, status_code=500)

    async with open_read_session() as db:
        document = await get_document_by_id(db, document_id=document_id)
        if not document:
            raise BusinessException(message="document not found for graph outbox event", code=4044, status_code=404)
        knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id=document.knowledge_base_id)
        user = await get_user_by_id(db, user_id=document.user_id)
        memory_entries = await list_memory_entries_by_document_id(db, document_id=document.id)
        if not knowledge_base or not user:
            raise BusinessException(
                message="graph outbox event missing user or knowledge base",
                code=5019,
                status_code=500,
            )
        await sync_document_memory_projection(
            db,
            user=user,
            knowledge_base=knowledge_base,
            document=document,
            memory_entries=memory_entries,
            rebuild_related_edges=True,
            raise_on_error=True,
        )

    return {
        "document_id": document_id,
        "memory_entry_count": len(memory_entries),
    }


async def apply_outbox_event(event: OutboxEvent) -> dict[str, Any]:
    if event.target_backend == settings.MEMORY_AGENT_OUTBOX_TARGET:
        return await apply_memory_agent_http_event(event)
    if event.event_type == EVENT_DOCUMENT_VECTOR_REINDEX:
        return await apply_vector_reindex_event(event)
    if event.event_type == EVENT_DOCUMENT_GRAPH_SYNC:
        return await apply_graph_sync_event(event)
    raise BusinessException(message=f"unsupported outbox event type: {event.event_type}", code=5020, status_code=500)


async def process_outbox_event_by_id(*, event_id: str) -> dict[str, Any]:
    event = await load_outbox_event_snapshot(event_id=event_id)
    if not event:
        raise BusinessException(message="outbox event not found", code=4046, status_code=404)

    if event.status == OUTBOX_SUCCEEDED:
        return {"event_id": event.id, "status": event.status, "skipped": True}
    if event.status not in {OUTBOX_PENDING, OUTBOX_FAILED}:
        return {"event_id": event.id, "status": event.status, "skipped": True}

    await mark_outbox_running(event=event)
    try:
        result = await apply_outbox_event(event)
    except Exception as exc:
        log_message = (
            f"outbox event failed event_id={event.id} event_type={event.event_type} "
            f"target_backend={event.target_backend} error_type={type(exc).__name__}"
        )
        logger = app_logger.bind(module="outbox")
        if event.target_backend == settings.MEMORY_AGENT_OUTBOX_TARGET:
            logger.error(log_message)
        else:
            logger.exception(f"{log_message} error={exc}")
        await mark_outbox_failed(event=event, exc=exc)
        raise

    await mark_outbox_succeeded(event_id=event.id)
    return {
        "event_id": event.id,
        "event_type": event.event_type,
        "target_backend": event.target_backend,
        "status": OUTBOX_SUCCEEDED,
        "result": result,
    }


async def dispatch_pending_outbox_events(
        *,
        limit: int = 20,
        target_backend: str | None = None,
) -> dict[str, int]:
    async with open_read_session() as db:
        events = await list_dispatchable_outbox_events(
            db,
            limit=limit,
            target_backend=target_backend,
            now=datetime.now(timezone.utc),
        )

    dispatched = 0
    failed = 0
    for event in events:
        try:
            await process_outbox_event_by_id(event_id=event.id)
            dispatched += 1
        except Exception:
            failed += 1

    return {
        "matched": len(events),
        "dispatched": dispatched,
        "failed": failed,
    }
