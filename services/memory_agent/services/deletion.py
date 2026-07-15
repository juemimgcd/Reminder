from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory_agent.contracts.events import AgentEventEnvelope
from services.memory_agent.database import open_write_session
from services.memory_agent.memory.identity import memory_slot_lock_key
from services.memory_agent.models.canonical_memory import CanonicalMemory
from services.memory_agent.models.document_projection import DocumentProjection
from services.memory_agent.models.evidence import Evidence, candidate_evidence, revision_evidence
from services.memory_agent.models.memory_candidate import MemoryCandidate
from services.memory_agent.models.memory_revision import MemoryRevision
from services.memory_agent.models.projection_batch import DocumentProjectionBatch
from services.memory_agent.repositories.memories import lock_memory_slot
from services.memory_agent.services.deletion_fences import (
    FenceSource,
    advance_deletion_fences,
    event_is_blocked_by_deletion,
)


class SourceDeletionError(ValueError):
    pass


class DocumentDeletedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_id: int = Field(gt=0)
    knowledge_base_id: str = Field(min_length=1, max_length=128)
    document_id: str = Field(min_length=1, max_length=128)
    source_version: datetime


class KnowledgeBaseDeletedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_id: int = Field(gt=0)
    knowledge_base_id: str = Field(min_length=1, max_length=128)
    source_version: datetime


class ConversationDeletedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_id: int = Field(gt=0)
    knowledge_base_id: str | None = Field(default=None, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    message_ids: list[str] = Field(default_factory=list)
    source_version: datetime

    @model_validator(mode="after")
    def message_ids_are_unique(self) -> "ConversationDeletedPayload":
        if len(self.message_ids) != len(set(self.message_ids)):
            raise ValueError("message_ids must be unique")
        if any(not message_id or len(message_id) > 128 for message_id in self.message_ids):
            raise ValueError("message_ids must contain identifiers of at most 128 characters")
        return self


@dataclass(frozen=True)
class DeletionResult:
    status: str
    completed_at: datetime
    projection_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    candidate_ids: tuple[str, ...]
    revision_ids: tuple[str, ...]
    memory_ids: tuple[str, ...]
    deleted_projection_count: int
    deleted_evidence_count: int
    deleted_candidate_count: int
    deleted_revision_count: int
    deleted_memory_count: int
    recalculated_memory_count: int


def _scope(column, knowledge_base_id: str | None):
    return column.is_(None) if knowledge_base_id is None else column == knowledge_base_id


async def _lock_affected_slots(
    db: AsyncSession,
    *,
    owner_id: int,
    knowledge_base_id: str | None,
    candidate_ids: set[str],
    memory_ids: set[str],
) -> None:
    slots = set(
        await db.execute(
            select(
                MemoryCandidate.memory_type,
                MemoryCandidate.subject,
                MemoryCandidate.predicate,
            ).where(MemoryCandidate.candidate_id.in_(candidate_ids))
        )
    ) if candidate_ids else set()
    if memory_ids:
        slots.update(
            await db.execute(
                select(
                    CanonicalMemory.memory_type,
                    CanonicalMemory.subject,
                    CanonicalMemory.predicate,
                ).where(CanonicalMemory.memory_id.in_(memory_ids))
            )
        )
    for memory_type, subject, predicate in sorted(slots):
        await lock_memory_slot(
            db,
            memory_slot_lock_key(
                owner_id=owner_id,
                knowledge_base_id=knowledge_base_id,
                memory_type=memory_type,
                subject=subject,
                predicate=predicate,
            ),
        )


async def delete_source_evidence(
    db: AsyncSession,
    *,
    owner_id: int,
    knowledge_base_id: str | None,
    source_type: str | None = None,
    source_ids: set[str] | None = None,
    source_document_id: str | None = None,
    delete_entire_scope: bool = False,
    projection_ids: set[str] | None = None,
    evidence_ids_to_delete: set[str] | None = None,
) -> DeletionResult:
    if not delete_entire_scope and (
        not source_ids and source_document_id is None and not evidence_ids_to_delete
    ):
        deleted_projection_ids = tuple(sorted(projection_ids or set()))
        return DeletionResult(
            status="succeeded",
            completed_at=datetime.now(UTC),
            projection_ids=deleted_projection_ids,
            evidence_ids=(),
            candidate_ids=(),
            revision_ids=(),
            memory_ids=(),
            deleted_projection_count=len(deleted_projection_ids),
            deleted_evidence_count=0,
            deleted_candidate_count=0,
            deleted_revision_count=0,
            deleted_memory_count=0,
            recalculated_memory_count=0,
        )

    evidence_filter = [
        Evidence.owner_id == owner_id,
        _scope(Evidence.knowledge_base_id, knowledge_base_id),
    ]
    if not delete_entire_scope:
        source_filters = []
        if evidence_ids_to_delete:
            source_filters.append(Evidence.evidence_id.in_(evidence_ids_to_delete))
        if source_ids:
            source_filter = Evidence.source_id.in_(source_ids)
            if source_type is not None:
                source_filter = and_(Evidence.source_type == source_type, source_filter)
            source_filters.append(source_filter)
        if source_document_id is not None:
            source_filters.append(
                and_(
                    Evidence.source_type == "document",
                    Evidence.source_document_id == source_document_id,
                )
            )
        evidence_filter.append(or_(*source_filters))

    evidence_ids = set(
        await db.scalars(
            select(Evidence.evidence_id).where(*evidence_filter).with_for_update()
        )
    )
    candidate_ids: set[str] = set()
    revision_ids: set[str] = set()
    memory_ids: set[str] = set()
    if evidence_ids:
        candidate_ids = set(
            await db.scalars(
                select(candidate_evidence.c.candidate_id).where(
                    candidate_evidence.c.evidence_id.in_(evidence_ids)
                )
            )
        )
        revision_ids = set(
            await db.scalars(
                select(revision_evidence.c.revision_id).where(
                    revision_evidence.c.evidence_id.in_(evidence_ids)
                )
            )
        )
        if revision_ids:
            memory_ids = set(
                await db.scalars(
                    select(MemoryRevision.memory_id).where(
                        MemoryRevision.revision_id.in_(revision_ids),
                        MemoryRevision.owner_id == owner_id,
                        _scope(MemoryRevision.knowledge_base_id, knowledge_base_id),
                    )
                )
            )

    if delete_entire_scope:
        candidate_ids.update(
            await db.scalars(
                select(MemoryCandidate.candidate_id).where(
                    MemoryCandidate.owner_id == owner_id,
                    _scope(MemoryCandidate.knowledge_base_id, knowledge_base_id),
                )
            )
        )
        memory_ids.update(
            await db.scalars(
                select(CanonicalMemory.memory_id).where(
                    CanonicalMemory.owner_id == owner_id,
                    _scope(CanonicalMemory.knowledge_base_id, knowledge_base_id),
                )
            )
        )

    await _lock_affected_slots(
        db,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        candidate_ids=candidate_ids,
        memory_ids=memory_ids,
    )
    if candidate_ids:
        await db.execute(
            select(MemoryCandidate)
            .where(MemoryCandidate.candidate_id.in_(candidate_ids))
            .with_for_update()
        )
    if memory_ids:
        await db.execute(
            select(CanonicalMemory)
            .where(CanonicalMemory.memory_id.in_(memory_ids))
            .with_for_update()
        )
        await db.execute(
            select(MemoryRevision)
            .where(MemoryRevision.memory_id.in_(memory_ids))
            .with_for_update()
        )

    deleted_evidence_count = 0
    if evidence_ids:
        deleted_evidence_count = (
            await db.execute(
                delete(Evidence)
                .where(Evidence.evidence_id.in_(evidence_ids))
                .returning(Evidence.evidence_id)
            )
        ).rowcount
        await db.flush()

    deleted_candidate_ids: set[str] = set()
    if candidate_ids:
        deleted_candidate_ids = set(
            await db.scalars(
                delete(MemoryCandidate)
                .where(
                    MemoryCandidate.candidate_id.in_(candidate_ids),
                    ~select(candidate_evidence.c.evidence_id)
                    .where(candidate_evidence.c.candidate_id == MemoryCandidate.candidate_id)
                    .exists(),
                )
                .returning(MemoryCandidate.candidate_id)
            )
        )

    deleted_memory_ids: set[str] = set()
    deleted_revision_ids: set[str] = set()
    recalculated_memory_ids: set[str] = set()
    if memory_ids:
        memories = list(
            await db.scalars(
                select(CanonicalMemory)
                .where(
                    CanonicalMemory.memory_id.in_(memory_ids),
                    CanonicalMemory.owner_id == owner_id,
                    _scope(CanonicalMemory.knowledge_base_id, knowledge_base_id),
                )
                .order_by(CanonicalMemory.memory_id)
                .with_for_update()
            )
        )
        for memory in memories:
            revisions = list(
                await db.scalars(
                    select(MemoryRevision)
                    .where(
                        MemoryRevision.memory_id == memory.memory_id,
                        MemoryRevision.owner_id == owner_id,
                        _scope(MemoryRevision.knowledge_base_id, knowledge_base_id),
                    )
                    .order_by(MemoryRevision.valid_from, MemoryRevision.revision_id)
                    .with_for_update()
                )
            )
            revision_evidence_counts = {
                revision.revision_id: int(
                    await db.scalar(
                        select(func.count(func.distinct(revision_evidence.c.evidence_id))).where(
                            revision_evidence.c.revision_id == revision.revision_id
                        )
                    )
                    or 0
                )
                for revision in revisions
            }
            supported_revisions = [
                revision
                for revision in revisions
                if revision_evidence_counts[revision.revision_id] > 0
            ]
            if not supported_revisions:
                deleted_revision_ids.update(
                    revision.revision_id for revision in revisions
                )
                deleted_memory_ids.add(memory.memory_id)
                await db.delete(memory)
                continue

            selected_revision = max(
                supported_revisions,
                key=lambda revision: (revision.valid_from, revision.revision_id),
            )
            active_revision = next(
                (
                    revision
                    for revision in revisions
                    if revision.revision_id == memory.active_revision_id
                ),
                None,
            )
            if active_revision is None:
                raise RuntimeError("canonical memory active revision is missing")
            if selected_revision.revision_id != active_revision.revision_id:
                now = datetime.now(UTC)
                active_revision.valid_to = max(active_revision.valid_from, now)
                await db.flush()
                selected_revision.valid_to = None
                memory.active_revision_id = selected_revision.revision_id
                memory.subject = selected_revision.subject
                memory.predicate = selected_revision.predicate
                memory.value = selected_revision.value
                memory.fingerprint = selected_revision.fingerprint
                memory.status = "active"
                await db.flush()

            unsupported_revision_ids = {
                revision.revision_id
                for revision in revisions
                if revision_evidence_counts[revision.revision_id] == 0
            }
            if unsupported_revision_ids:
                deleted_revision_ids.update(
                    await db.scalars(
                        delete(MemoryRevision)
                        .where(MemoryRevision.revision_id.in_(unsupported_revision_ids))
                        .returning(MemoryRevision.revision_id)
                    )
                )

            evidence_count = int(
                await db.scalar(
                    select(func.count(func.distinct(revision_evidence.c.evidence_id)))
                    .select_from(MemoryRevision)
                    .join(
                        revision_evidence,
                        revision_evidence.c.revision_id == MemoryRevision.revision_id,
                    )
                    .where(MemoryRevision.memory_id == memory.memory_id)
                )
                or 0
            )
            confidence_ceiling = 1.0 - (0.5**evidence_count)
            memory.confidence = min(memory.confidence, confidence_ceiling)
            recalculated_memory_ids.add(memory.memory_id)

    deleted_projection_ids = tuple(sorted(projection_ids or set()))
    return DeletionResult(
        status="succeeded",
        completed_at=datetime.now(UTC),
        projection_ids=deleted_projection_ids,
        evidence_ids=tuple(sorted(evidence_ids)),
        candidate_ids=tuple(sorted(deleted_candidate_ids)),
        revision_ids=tuple(sorted(deleted_revision_ids)),
        memory_ids=tuple(sorted(deleted_memory_ids)),
        deleted_projection_count=len(deleted_projection_ids),
        deleted_evidence_count=deleted_evidence_count,
        deleted_candidate_count=len(deleted_candidate_ids),
        deleted_revision_count=len(deleted_revision_ids),
        deleted_memory_count=len(deleted_memory_ids),
        recalculated_memory_count=len(recalculated_memory_ids),
    )


async def delete_document_projection(
    db: AsyncSession,
    *,
    owner_id: int,
    knowledge_base_id: str,
    document_id: str,
) -> DeletionResult:
    projections = list(
        await db.scalars(
            select(DocumentProjection)
            .where(
                DocumentProjection.owner_id == owner_id,
                DocumentProjection.knowledge_base_id == knowledge_base_id,
                DocumentProjection.document_id == document_id,
            )
            .with_for_update()
        )
    )
    projection_ids = {projection.projection_id for projection in projections}
    chunk_ids = set()
    if projection_ids:
        from services.memory_agent.models.document_chunk import DocumentChunk

        chunk_ids = set(
            await db.scalars(
                select(DocumentChunk.chunk_id).where(
                    DocumentChunk.projection_id.in_(projection_ids)
                )
            )
        )
        batches = list(
            await db.scalars(
                select(DocumentProjectionBatch).where(
                    DocumentProjectionBatch.projection_id.in_(projection_ids)
                )
            )
        )
        chunk_ids.update(
            str(chunk["chunk_id"])
            for batch in batches
            for chunk in batch.chunks
            if isinstance(chunk.get("chunk_id"), str) and chunk["chunk_id"]
        )
        await db.execute(
            delete(DocumentProjection).where(
                DocumentProjection.projection_id.in_(projection_ids)
            )
        )
        await db.flush()
    return await delete_source_evidence(
        db,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        source_type="document",
        source_ids=chunk_ids,
        source_document_id=document_id,
        projection_ids=projection_ids,
    )


def _validate_scope(event: AgentEventEnvelope, payload) -> None:
    if payload.owner_id != event.owner_id or payload.knowledge_base_id != event.knowledge_base_id:
        raise SourceDeletionError("deletion payload scope does not match its envelope")


async def handle_document_deleted(event: AgentEventEnvelope) -> DeletionResult:
    try:
        payload = DocumentDeletedPayload.model_validate(event.payload)
    except ValueError as exc:
        raise SourceDeletionError("invalid document deletion payload") from exc
    _validate_scope(event, payload)
    if await event_is_blocked_by_deletion(
        event,
        sources=[FenceSource(source_type="document", source_id=payload.document_id)],
    ):
        async with open_write_session() as db:
            return await delete_source_evidence(
                db,
                owner_id=event.owner_id,
                knowledge_base_id=payload.knowledge_base_id,
                source_type="document",
                source_ids=set(),
            )
    async with open_write_session() as db:
        advanced = await advance_deletion_fences(
            db,
            event=event,
            primary=FenceSource(source_type="document", source_id=payload.document_id),
        )
        if not advanced:
            return await delete_source_evidence(
                db,
                owner_id=event.owner_id,
                knowledge_base_id=payload.knowledge_base_id,
                source_type="document",
                source_ids=set(),
            )
        return await delete_document_projection(
            db,
            owner_id=event.owner_id,
            knowledge_base_id=payload.knowledge_base_id,
            document_id=payload.document_id,
        )


async def handle_knowledge_base_deleted(event: AgentEventEnvelope) -> DeletionResult:
    try:
        payload = KnowledgeBaseDeletedPayload.model_validate(event.payload)
    except ValueError as exc:
        raise SourceDeletionError("invalid knowledge base deletion payload") from exc
    _validate_scope(event, payload)
    async with open_write_session() as db:
        advanced = await advance_deletion_fences(
            db,
            event=event,
            primary=FenceSource(
                source_type="knowledge_base",
                source_id=payload.knowledge_base_id,
            ),
        )
        if not advanced:
            return await delete_source_evidence(
                db,
                owner_id=event.owner_id,
                knowledge_base_id=payload.knowledge_base_id,
                source_type="document",
                source_ids=set(),
            )
        projection_ids = set(
            await db.scalars(
                select(DocumentProjection.projection_id)
                .where(
                    DocumentProjection.owner_id == event.owner_id,
                    DocumentProjection.knowledge_base_id == payload.knowledge_base_id,
                )
                .with_for_update()
            )
        )
        if projection_ids:
            await db.execute(
                delete(DocumentProjection).where(
                    DocumentProjection.projection_id.in_(projection_ids)
                )
            )
        return await delete_source_evidence(
            db,
            owner_id=event.owner_id,
            knowledge_base_id=payload.knowledge_base_id,
            delete_entire_scope=True,
            projection_ids=projection_ids,
        )


async def handle_conversation_deleted(event: AgentEventEnvelope) -> DeletionResult:
    try:
        payload = ConversationDeletedPayload.model_validate(event.payload)
    except ValueError as exc:
        raise SourceDeletionError("invalid conversation deletion payload") from exc
    _validate_scope(event, payload)
    if await event_is_blocked_by_deletion(
        event,
        sources=[
            FenceSource(source_type="conversation", source_id=payload.session_id),
            *[
                FenceSource(source_type="explicit_request", source_id=message_id)
                for message_id in payload.message_ids
            ],
        ],
    ):
        async with open_write_session() as db:
            return await delete_source_evidence(
                db,
                owner_id=event.owner_id,
                knowledge_base_id=event.knowledge_base_id,
                source_type="conversation",
                source_ids=set(),
            )
    async with open_write_session() as db:
        advanced = await advance_deletion_fences(
            db,
            event=event,
            primary=FenceSource(
                source_type="conversation",
                source_id=payload.session_id,
            ),
            additional=[
                FenceSource(source_type="explicit_request", source_id=message_id)
                for message_id in payload.message_ids
            ],
        )
        if not advanced:
            return await delete_source_evidence(
                db,
                owner_id=event.owner_id,
                knowledge_base_id=event.knowledge_base_id,
                source_type="conversation",
                source_ids=set(),
            )
        conversation_result = await delete_source_evidence(
            db,
            owner_id=event.owner_id,
            knowledge_base_id=event.knowledge_base_id,
            source_type="conversation",
            source_ids={payload.session_id},
        )
        explicit_result = await delete_source_evidence(
            db,
            owner_id=event.owner_id,
            knowledge_base_id=event.knowledge_base_id,
            source_type="explicit_request",
            source_ids=set(payload.message_ids),
        )
        return DeletionResult(
            status="succeeded",
            completed_at=datetime.now(UTC),
            projection_ids=(),
            evidence_ids=tuple(sorted(set(conversation_result.evidence_ids + explicit_result.evidence_ids))),
            candidate_ids=tuple(sorted(set(conversation_result.candidate_ids + explicit_result.candidate_ids))),
            revision_ids=tuple(sorted(set(conversation_result.revision_ids + explicit_result.revision_ids))),
            memory_ids=tuple(sorted(set(conversation_result.memory_ids + explicit_result.memory_ids))),
            deleted_projection_count=0,
            deleted_evidence_count=(
                conversation_result.deleted_evidence_count + explicit_result.deleted_evidence_count
            ),
            deleted_candidate_count=(
                conversation_result.deleted_candidate_count + explicit_result.deleted_candidate_count
            ),
            deleted_revision_count=(
                conversation_result.deleted_revision_count + explicit_result.deleted_revision_count
            ),
            deleted_memory_count=(
                conversation_result.deleted_memory_count + explicit_result.deleted_memory_count
            ),
            recalculated_memory_count=(
                conversation_result.recalculated_memory_count
                + explicit_result.recalculated_memory_count
            ),
        )
