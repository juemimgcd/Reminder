import hashlib
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory_agent.contracts.events import AgentEventEnvelope
from services.memory_agent.database import engine, open_read_session, open_write_session
from services.memory_agent.memory.extraction import extract_candidates
from services.memory_agent.memory.identity import (
    evidence_identity,
    memory_fingerprint,
    normalize_memory_text,
)
from services.memory_agent.memory.reconciliation import (
    EvidenceInput as ReconciliationEvidenceInput,
)
from services.memory_agent.memory.reconciliation import reconcile_candidate
from services.memory_agent.memory.schemas import (
    ConversationCompletedPayload,
    EvidenceInput,
    MemoryRequestedPayload,
    MemorySettingsChangedPayload,
)
from services.memory_agent.memory.sensitivity import classify_sensitivity, contains_secret
from services.memory_agent.models.document_chunk import DocumentChunk
from services.memory_agent.models.document_projection import DocumentProjection
from services.memory_agent.models.evidence import Evidence, candidate_evidence
from services.memory_agent.models.inbox_event import InboxEvent
from services.memory_agent.models.memory_candidate import MemoryCandidate
from services.memory_agent.models.memory_settings import MemorySettings


class MalformedMemoryEvent(ValueError):
    pass


def _payload(model, event: AgentEventEnvelope):
    try:
        return model.model_validate(event.payload)
    except ValidationError as exc:
        raise MalformedMemoryEvent("invalid memory event payload") from exc


def _event_order(event: AgentEventEnvelope) -> tuple[datetime, str]:
    return event.occurred_at, event.event_id


async def _apply_settings(db: AsyncSession, event: AgentEventEnvelope) -> None:
    payload = _payload(MemorySettingsChangedPayload, event)
    row = await db.scalar(
        select(MemorySettings)
        .where(MemorySettings.owner_id == event.owner_id)
        .with_for_update()
    )
    if row is None:
        row = MemorySettings(owner_id=event.owner_id)
        db.add(row)
        await db.flush()
    current_order = (
        (row.last_event_occurred_at, row.last_event_id)
        if row.last_event_occurred_at is not None and row.last_event_id is not None
        else None
    )
    if current_order is not None and _event_order(event) <= current_order:
        return
    row.automatic_conversation_memory = payload.automatic_conversation_memory
    row.last_event_occurred_at = event.occurred_at
    row.last_event_id = event.event_id
    await db.flush()


async def _apply_earlier_pending_settings(
    db: AsyncSession,
    event: AgentEventEnvelope,
) -> None:
    rows = list(
        await db.scalars(
            select(InboxEvent)
            .where(
                InboxEvent.status == "pending",
                InboxEvent.payload["event_type"].astext == "user.memory_settings.changed",
                InboxEvent.payload["owner_id"].astext == str(event.owner_id),
            )
            .with_for_update()
        )
    )
    ordered: list[tuple[AgentEventEnvelope, InboxEvent]] = []
    for row in rows:
        try:
            settings_event = AgentEventEnvelope.model_validate(row.payload)
        except ValidationError:
            row.status = "failed"
            row.processed_at = datetime.now(UTC)
            row.last_error = "invalid settings event envelope"
            continue
        if _event_order(settings_event) < _event_order(event):
            ordered.append((settings_event, row))
    for settings_event, row in sorted(ordered, key=lambda item: _event_order(item[0])):
        try:
            await _apply_settings(db, settings_event)
        except MalformedMemoryEvent as exc:
            row.status = "failed"
            row.last_error = str(exc)
        else:
            row.status = "succeeded"
            row.last_error = None
        row.processed_at = datetime.now(UTC)


async def _automatic_conversation_enabled(event: AgentEventEnvelope) -> bool:
    lock_identity = f"memory-owner:{event.owner_id}"
    async with engine.connect() as connection:
        await connection.execute(
            text("SELECT pg_advisory_lock(hashtextextended(:identity, 2))"),
            {"identity": lock_identity},
        )
        await connection.commit()
        try:
            async with AsyncSession(bind=connection, expire_on_commit=False) as db:
                async with db.begin():
                    await _apply_earlier_pending_settings(db, event)
                    row = await db.get(MemorySettings, event.owner_id)
                    return bool(row and row.automatic_conversation_memory)
        finally:
            await connection.execute(
                text("SELECT pg_advisory_unlock(hashtextextended(:identity, 2))"),
                {"identity": lock_identity},
            )
            await connection.commit()


async def handle_memory_settings_changed(event: AgentEventEnvelope) -> None:
    lock_identity = f"memory-owner:{event.owner_id}"
    async with engine.connect() as connection:
        await connection.execute(
            text("SELECT pg_advisory_lock(hashtextextended(:identity, 2))"),
            {"identity": lock_identity},
        )
        await connection.commit()
        try:
            async with AsyncSession(bind=connection, expire_on_commit=False) as db:
                async with db.begin():
                    await _apply_settings(db, event)
        finally:
            await connection.execute(
                text("SELECT pg_advisory_unlock(hashtextextended(:identity, 2))"),
                {"identity": lock_identity},
            )
            await connection.commit()


async def _already_reconciled(
    db: AsyncSession,
    *,
    owner_id: int,
    knowledge_base_id: str | None,
    candidate,
    reconciliation_evidence: ReconciliationEvidenceInput,
) -> bool:
    identity_hash = evidence_identity(
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        source_type=reconciliation_evidence.source_type,
        source_id=reconciliation_evidence.source_id,
        source_version=reconciliation_evidence.source_version,
        content_hash=reconciliation_evidence.content_hash,
    )
    fingerprint = memory_fingerprint(
        subject=normalize_memory_text(candidate.subject),
        predicate=normalize_memory_text(candidate.predicate),
        value=normalize_memory_text(candidate.value),
    )
    return (
        await db.scalar(
            select(MemoryCandidate.candidate_id)
            .join(
                candidate_evidence,
                candidate_evidence.c.candidate_id == MemoryCandidate.candidate_id,
            )
            .join(Evidence, Evidence.evidence_id == candidate_evidence.c.evidence_id)
            .where(
                MemoryCandidate.owner_id == owner_id,
                MemoryCandidate.fingerprint == fingerprint,
                Evidence.identity_hash == identity_hash,
            )
            .limit(1)
        )
        is not None
    )


async def _extract_and_reconcile(
    evidence: EvidenceInput,
    *,
    owner_id: int,
    knowledge_base_id: str | None,
    explicit_request: bool,
) -> None:
    if contains_secret(evidence.excerpt):
        return
    candidates = await extract_candidates(evidence)
    for candidate in candidates:
        # Re-scan model fields immediately before deterministic policy and persistence.
        sensitivity = classify_sensitivity(
            candidate.subject,
            candidate.predicate,
            candidate.evidence_quote,
            candidate.value,
            model_signals=candidate.sensitivity_signals,
        )
        if sensitivity == "secret":
            continue
        content_hash = hashlib.sha256(candidate.evidence_quote.encode("utf-8")).hexdigest()
        stored_evidence = ReconciliationEvidenceInput(
            source_type=evidence.source_type,
            source_id=evidence.source_id,
            source_version=evidence.source_version,
            minimum_text=candidate.evidence_quote,
            content_hash=content_hash,
            occurred_at=evidence.occurred_at,
        )
        async with open_write_session() as db:
            if await _already_reconciled(
                db,
                owner_id=owner_id,
                knowledge_base_id=knowledge_base_id,
                candidate=candidate,
                reconciliation_evidence=stored_evidence,
            ):
                continue
            await reconcile_candidate(
                db,
                owner_id=owner_id,
                knowledge_base_id=knowledge_base_id,
                memory_type=candidate.memory_type,
                subject=candidate.subject,
                predicate=candidate.predicate,
                value=candidate.value,
                confidence=candidate.confidence,
                sensitivity=sensitivity,
                evidence=[stored_evidence],
                extraction_provenance={
                    "source_type": evidence.source_type,
                    "evidence_start": candidate.evidence_start,
                    "evidence_end": candidate.evidence_end,
                    "temporal_hints": candidate.temporal_hints.model_dump(mode="json"),
                },
                explicit_request=explicit_request,
                actor="memory-extraction",
            )


async def handle_conversation_completed(event: AgentEventEnvelope) -> None:
    payload = _payload(ConversationCompletedPayload, event)
    if not await _automatic_conversation_enabled(event):
        return
    excerpt = (
        f"User:\n{payload.user_message.content}\n\n"
        f"Assistant:\n{payload.assistant_message.content}"
    )[:20_000]
    await _extract_and_reconcile(
        EvidenceInput(
            source_type="conversation",
            source_id=payload.session_id,
            source_version=payload.assistant_message.id,
            excerpt=excerpt,
            occurred_at=payload.assistant_message.created_at,
        ),
        owner_id=event.owner_id,
        knowledge_base_id=event.knowledge_base_id,
        explicit_request=False,
    )


async def handle_user_memory_requested(event: AgentEventEnvelope) -> None:
    payload = _payload(MemoryRequestedPayload, event)
    await _extract_and_reconcile(
        EvidenceInput(
            source_type="explicit_request",
            source_id=payload.message_id,
            source_version=payload.message_created_at.isoformat(),
            excerpt=payload.excerpt,
            occurred_at=payload.message_created_at,
        ),
        owner_id=event.owner_id,
        knowledge_base_id=event.knowledge_base_id,
        explicit_request=True,
    )


async def handle_document_projection(
    event: AgentEventEnvelope,
    *,
    projection_id: str,
) -> None:
    async with open_read_session() as db:
        projection = await db.get(DocumentProjection, projection_id)
        if projection is None or projection.status != "active":
            return
        chunks = list(
            await db.scalars(
                select(DocumentChunk)
                .where(
                    DocumentChunk.projection_id == projection_id,
                    DocumentChunk.is_active.is_(True),
                )
                .order_by(DocumentChunk.chunk_index)
            )
        )
    occurred_at = projection.activated_at or event.occurred_at
    for chunk in chunks:
        await _extract_and_reconcile(
            EvidenceInput(
                source_type="document",
                source_id=chunk.chunk_id,
                source_version=chunk.document_version,
                excerpt=chunk.content[:20_000],
                occurred_at=occurred_at,
            ),
            owner_id=event.owner_id,
            knowledge_base_id=event.knowledge_base_id,
            explicit_request=False,
        )


async def is_retry_attempt(event_id: str) -> bool:
    async with open_read_session() as db:
        attempt_count = await db.scalar(
            select(InboxEvent.attempt_count).where(InboxEvent.event_id == event_id)
        )
    return bool(attempt_count and attempt_count > 1)
