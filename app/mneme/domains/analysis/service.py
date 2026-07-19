from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.crud.knowledge_base import get_knowledge_base_by_id
from app.mneme.domains.tasks.state import is_active_task_status
from app.mneme.models.chunk import Chunk
from app.mneme.models.document import Document
from app.mneme.models.memory_entry import MemoryEntry
from app.mneme.models.outbox_event import OutboxEvent
from app.mneme.models.task_record import TaskRecord
from app.mneme.schemas.analytics import (
    BackendStatusData,
    ChunkAnalyticsData,
    DocumentAnalyticsData,
    KnowledgeBaseAnalyticsReportData,
    MemoryAnalyticsData,
    OutboxAnalyticsData,
    StatusCountData,
    TaskAnalyticsData,
)
from app.mneme.utils.exceptions import BusinessException


def get_field(item: Any, field_name: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(field_name, default)
    return getattr(item, field_name, default)


def build_status_counts(items: list[Any], field_name: str) -> list[StatusCountData]:
    counter = Counter(str(get_field(item, field_name, "unknown") or "unknown") for item in items)
    return [
        StatusCountData(name=name, count=count)
        for name, count in sorted(counter.items())
    ]


def count_unique(items: list[Any], field_name: str) -> int:
    return len(
        {
            get_field(item, field_name)
            for item in items
            if get_field(item, field_name) is not None
        }
    )


def build_backend_status(items: list[Any]) -> list[BackendStatusData]:
    buckets: dict[str, list[Any]] = defaultdict(list)
    for item in items:
        buckets[str(get_field(item, "target_backend", "unknown") or "unknown")].append(item)

    return [
        BackendStatusData(
            backend=backend,
            status_counts=build_status_counts(bucket, "status"),
            total=len(bucket),
        )
        for backend, bucket in sorted(buckets.items())
    ]


def render_status_counts(counts: list[StatusCountData]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{item.name}={item.count}" for item in counts)


def build_markdown_report(report: KnowledgeBaseAnalyticsReportData) -> str:
    return "\n".join(
        [
            f"# Knowledge Base Analytics: {report.knowledge_base_id}",
            "",
            f"- generated_at: {report.generated_at.isoformat()}",
            f"- documents: {report.documents.document_count}",
            f"- document_status: {render_status_counts(report.documents.status_counts)}",
            f"- chunks: {report.chunks.chunk_count}",
            f"- avg_chunks_per_document: {report.chunks.avg_chunks_per_document:.2f}",
            f"- sections: {report.chunks.section_count}",
            f"- memory_entries: {report.memory.memory_entry_count}",
            f"- memory_types: {render_status_counts(report.memory.entry_type_counts)}",
            f"- tasks: {report.tasks.task_count}",
            f"- active_tasks: {report.tasks.active_task_count}",
            f"- failed_tasks: {report.tasks.failed_task_count}",
            f"- task_status: {render_status_counts(report.tasks.status_counts)}",
            f"- outbox_events: {report.outbox.event_count}",
            f"- outbox_failed: {report.outbox.failed_event_count}",
            f"- outbox_dead_letter: {report.outbox.dead_letter_count}",
        ]
    )


def build_analytics_report_from_snapshots(
        *,
        knowledge_base_id: str,
        documents: list[Any],
        chunks: list[Any],
        memory_entries: list[Any],
        task_records: list[Any],
        outbox_events: list[Any],
        generated_at: datetime | None = None,
) -> KnowledgeBaseAnalyticsReportData:
    generated_at = generated_at or datetime.now(timezone.utc)
    document_count = len(documents)
    total_file_size = sum(int(get_field(document, "file_size", 0) or 0) for document in documents)
    chunk_count = len(chunks)
    section_count = count_unique(chunks, "section_id")
    avg_chunks_per_document = chunk_count / document_count if document_count else 0.0
    active_task_count = sum(
        1
        for task in task_records
        if is_active_task_status(str(get_field(task, "status", "")))
    )
    failed_task_count = sum(
        1
        for task in task_records
        if str(get_field(task, "status", "")) == "failed"
    )
    failed_event_count = sum(
        1
        for event in outbox_events
        if str(get_field(event, "status", "")) == "failed"
    )
    dead_letter_count = sum(
        1
        for event in outbox_events
        if str(get_field(event, "status", "")) == "dead_letter"
    )

    report = KnowledgeBaseAnalyticsReportData(
        knowledge_base_id=knowledge_base_id,
        generated_at=generated_at,
        documents=DocumentAnalyticsData(
            document_count=document_count,
            total_file_size=total_file_size,
            status_counts=build_status_counts(documents, "status"),
        ),
        chunks=ChunkAnalyticsData(
            chunk_count=chunk_count,
            avg_chunks_per_document=avg_chunks_per_document,
            section_count=section_count,
        ),
        memory=MemoryAnalyticsData(
            memory_entry_count=len(memory_entries),
            entry_type_counts=build_status_counts(memory_entries, "entry_type"),
        ),
        tasks=TaskAnalyticsData(
            task_count=len(task_records),
            active_task_count=active_task_count,
            failed_task_count=failed_task_count,
            status_counts=build_status_counts(task_records, "status"),
        ),
        outbox=OutboxAnalyticsData(
            event_count=len(outbox_events),
            failed_event_count=failed_event_count,
            dead_letter_count=dead_letter_count,
            backend_status=build_backend_status(outbox_events),
        ),
        markdown="",
    )
    report.markdown = build_markdown_report(report)
    return report


async def load_knowledge_base_analytics_snapshots(
        db: AsyncSession,
        *,
        knowledge_base_pk: int,
        knowledge_base_id: str,
        user_id: int,
) -> tuple[list[Document], list[Chunk], list[MemoryEntry], list[TaskRecord], list[OutboxEvent]]:
    document_result = await db.execute(
        select(Document)
        .where(Document.knowledge_base_pk == knowledge_base_pk)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.asc())
    )
    documents = list(document_result.scalars().all())
    document_ids = [document.id for document in documents]

    chunk_result = await db.execute(
        select(Chunk)
        .join(Document, Chunk.document_pk == Document.pk)
        .where(Document.knowledge_base_pk == knowledge_base_pk)
        .where(Document.user_id == user_id)
        .order_by(Chunk.document_pk.asc(), Chunk.chunk_index.asc())
    )
    chunks = list(chunk_result.scalars().all())

    memory_result = await db.execute(
        select(MemoryEntry)
        .where(MemoryEntry.knowledge_base_pk == knowledge_base_pk)
        .where(MemoryEntry.user_id == user_id)
        .order_by(MemoryEntry.created_at.asc())
    )
    memory_entries = list(memory_result.scalars().all())

    task_records: list[TaskRecord] = []
    outbox_events: list[OutboxEvent] = []
    if document_ids:
        task_result = await db.execute(
            select(TaskRecord)
            .where(TaskRecord.task_type == "document_index")
            .where(TaskRecord.target_id.in_(document_ids))
            .order_by(TaskRecord.created_at.asc())
        )
        task_records = list(task_result.scalars().all())

        outbox_result = await db.execute(
            select(OutboxEvent)
            .where(OutboxEvent.aggregate_type == "document")
            .where(OutboxEvent.aggregate_id.in_(document_ids))
            .order_by(OutboxEvent.created_at.asc())
        )
        outbox_events = list(outbox_result.scalars().all())

    return documents, chunks, memory_entries, task_records, outbox_events


async def build_knowledge_base_analytics_report(
        db: AsyncSession,
        *,
        user_id: int,
        knowledge_base_id: str,
) -> KnowledgeBaseAnalyticsReportData:
    knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id=knowledge_base_id)
    if not knowledge_base:
        raise BusinessException(message="knowledge base not found", code=4042, status_code=404)
    if knowledge_base.user_id != user_id:
        raise BusinessException(message="knowledge base does not belong to current user", code=4007, status_code=403)

    documents, chunks, memory_entries, task_records, outbox_events = await load_knowledge_base_analytics_snapshots(
        db,
        knowledge_base_pk=knowledge_base.pk,
        knowledge_base_id=knowledge_base.id,
        user_id=user_id,
    )
    return build_analytics_report_from_snapshots(
        knowledge_base_id=knowledge_base.id,
        documents=documents,
        chunks=chunks,
        memory_entries=memory_entries,
        task_records=task_records,
        outbox_events=outbox_events,
    )
