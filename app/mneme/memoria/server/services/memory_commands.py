from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.memoria.server.memory.identity import memory_slot_lock_key
from app.mneme.memoria.server.memory.reconciliation import confirm_candidate, reject_candidate, revise_memory
from app.mneme.memoria.server.models.canonical_memory import CanonicalMemory
from app.mneme.memoria.server.models.evidence import Evidence, revision_evidence
from app.mneme.memoria.server.models.memory_audit import MemoryActionAudit
from app.mneme.memoria.server.models.memory_candidate import MemoryCandidate
from app.mneme.memoria.server.models.memory_revision import MemoryRevision
from app.mneme.memoria.server.repositories.memories import (
    hard_delete_memory,
    load_memory_for_update,
    lock_memory_slot,
    new_id,
)
from app.mneme.memoria.server.services.deletion import DeletionResult, delete_source_evidence


@dataclass(frozen=True)
class PurgeCounts:
    evidence: int = 0
    candidates: int = 0
    revisions: int = 0
    memories: int = 0

    def add(self, result: DeletionResult) -> "PurgeCounts":
        return PurgeCounts(
            evidence=self.evidence + result.deleted_evidence_count,
            candidates=self.candidates + result.deleted_candidate_count,
            revisions=self.revisions + result.deleted_revision_count,
            memories=self.memories + result.deleted_memory_count,
        )


class PurgeConfirmationReplay(ValueError):
    pass


def _scope(column, knowledge_base_id: str | None):
    return column.is_(None) if knowledge_base_id is None else column == knowledge_base_id


def _audit(
    db: AsyncSession,
    *,
    owner_id: int,
    knowledge_base_id: str | None,
    action: str,
    target_type: str,
    target_id: str,
    actor_id: str,
    reason: str,
    confirmation_jti: str | None = None,
) -> None:
    db.add(
        MemoryActionAudit(
            audit_id=new_id(),
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            actor_id=actor_id,
            reason=reason,
            confirmation_jti=confirmation_jti,
        )
    )


async def confirm(
    db: AsyncSession, *, candidate_id: str, owner_id: int, knowledge_base_id: str | None, actor_id: str, reason: str
) -> CanonicalMemory:
    identity = await db.execute(
        select(MemoryCandidate.memory_type, MemoryCandidate.subject, MemoryCandidate.predicate).where(
            MemoryCandidate.candidate_id == candidate_id,
            MemoryCandidate.owner_id == owner_id,
            _scope(MemoryCandidate.knowledge_base_id, knowledge_base_id),
        )
    )
    slot = identity.one_or_none()
    if slot is None:
        raise LookupError("candidate not found in owner scope")
    await lock_memory_slot(
        db,
        memory_slot_lock_key(
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            memory_type=slot.memory_type,
            subject=slot.subject,
            predicate=slot.predicate,
        ),
    )
    memory = await confirm_candidate(
        db, candidate_id=candidate_id, owner_id=owner_id, knowledge_base_id=knowledge_base_id, actor=actor_id
    )
    _audit(
        db,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        action="confirm",
        target_type="candidate",
        target_id=candidate_id,
        actor_id=actor_id,
        reason=reason,
    )
    return memory


async def reject(
    db: AsyncSession, *, candidate_id: str, owner_id: int, knowledge_base_id: str | None, actor_id: str, reason: str
) -> MemoryCandidate:
    identity = await db.execute(
        select(MemoryCandidate.memory_type, MemoryCandidate.subject, MemoryCandidate.predicate).where(
            MemoryCandidate.candidate_id == candidate_id,
            MemoryCandidate.owner_id == owner_id,
            _scope(MemoryCandidate.knowledge_base_id, knowledge_base_id),
        )
    )
    slot = identity.one_or_none()
    if slot is None:
        raise LookupError("candidate not found in owner scope")
    await lock_memory_slot(
        db,
        memory_slot_lock_key(
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            memory_type=slot.memory_type,
            subject=slot.subject,
            predicate=slot.predicate,
        ),
    )
    candidate = await reject_candidate(
        db, candidate_id=candidate_id, owner_id=owner_id, knowledge_base_id=knowledge_base_id
    )
    _audit(
        db,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        action="reject",
        target_type="candidate",
        target_id=candidate_id,
        actor_id=actor_id,
        reason=reason,
    )
    return candidate


async def revise(
    db: AsyncSession,
    *,
    memory_id: str,
    owner_id: int,
    knowledge_base_id: str | None,
    subject: str,
    predicate: str,
    value: str,
    confidence: float | None,
    actor_id: str,
    reason: str,
) -> CanonicalMemory:
    current = await db.execute(
        select(CanonicalMemory.memory_type, CanonicalMemory.subject, CanonicalMemory.predicate).where(
            CanonicalMemory.memory_id == memory_id,
            CanonicalMemory.owner_id == owner_id,
            _scope(CanonicalMemory.knowledge_base_id, knowledge_base_id),
        )
    )
    old_slot = current.one_or_none()
    if old_slot is None:
        raise LookupError("memory not found in owner scope")
    slots = {
        (old_slot.memory_type, old_slot.subject, old_slot.predicate),
        (old_slot.memory_type, subject, predicate),
    }
    for memory_type, slot_subject, slot_predicate in sorted(slots):
        await lock_memory_slot(
            db,
            memory_slot_lock_key(
                owner_id=owner_id,
                knowledge_base_id=knowledge_base_id,
                memory_type=memory_type,
                subject=slot_subject,
                predicate=slot_predicate,
            ),
        )
    memory = await revise_memory(
        db,
        memory_id=memory_id,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        subject=subject,
        predicate=predicate,
        value=value,
        confidence=confidence,
        actor=actor_id,
        reason=reason,
    )
    _audit(
        db,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        action="revise",
        target_type="memory",
        target_id=memory_id,
        actor_id=actor_id,
        reason=reason,
    )
    return memory


async def invalidate(
    db: AsyncSession, *, memory_id: str, owner_id: int, knowledge_base_id: str | None, actor_id: str, reason: str
) -> CanonicalMemory:
    identity = await db.execute(
        select(CanonicalMemory.memory_type, CanonicalMemory.subject, CanonicalMemory.predicate).where(
            CanonicalMemory.memory_id == memory_id,
            CanonicalMemory.owner_id == owner_id,
            _scope(CanonicalMemory.knowledge_base_id, knowledge_base_id),
        )
    )
    slot = identity.one_or_none()
    if slot is None:
        raise LookupError("memory not found in owner scope")
    await lock_memory_slot(
        db,
        memory_slot_lock_key(
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            memory_type=slot.memory_type,
            subject=slot.subject,
            predicate=slot.predicate,
        ),
    )
    memory = await load_memory_for_update(
        db, memory_id=memory_id, owner_id=owner_id, knowledge_base_id=knowledge_base_id
    )
    if memory is None:
        raise LookupError("memory not found in owner scope")
    if memory.status != "active":
        raise ValueError("only active memories can be invalidated")
    memory.status = "invalidated"
    memory.updated_at = datetime.now(UTC)
    _audit(
        db,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        action="invalidate",
        target_type="memory",
        target_id=memory_id,
        actor_id=actor_id,
        reason=reason,
    )
    await db.flush()
    return memory


async def hard_delete(
    db: AsyncSession, *, memory_id: str, owner_id: int, knowledge_base_id: str | None, actor_id: str, reason: str
) -> None:
    identity = await db.execute(
        select(CanonicalMemory.memory_type, CanonicalMemory.subject, CanonicalMemory.predicate).where(
            CanonicalMemory.memory_id == memory_id,
            CanonicalMemory.owner_id == owner_id,
            _scope(CanonicalMemory.knowledge_base_id, knowledge_base_id),
        )
    )
    slot = identity.one_or_none()
    if slot is None:
        raise LookupError("memory not found in owner scope")
    evidence_ids = set(
        await db.scalars(
            select(revision_evidence.c.evidence_id)
            .join(MemoryRevision, MemoryRevision.revision_id == revision_evidence.c.revision_id)
            .where(MemoryRevision.memory_id == memory_id)
        )
    )
    if evidence_ids:
        await delete_source_evidence(
            db,
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            evidence_ids_to_delete=evidence_ids,
        )
    else:
        await lock_memory_slot(
            db,
            memory_slot_lock_key(
                owner_id=owner_id,
                knowledge_base_id=knowledge_base_id,
                memory_type=slot.memory_type,
                subject=slot.subject,
                predicate=slot.predicate,
            ),
        )
    await hard_delete_memory(db, memory_id=memory_id, owner_id=owner_id, knowledge_base_id=knowledge_base_id)
    _audit(
        db,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        action="hard_delete",
        target_type="memory",
        target_id=memory_id,
        actor_id=actor_id,
        reason=reason,
    )


async def purge_source(
    db: AsyncSession, *, owner_id: int, knowledge_base_id: str | None, source_id: str
) -> PurgeCounts:
    return PurgeCounts().add(
        await delete_source_evidence(
            db,
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            source_ids={source_id},
            source_document_id=source_id,
        )
    )


async def purge_knowledge_base(db: AsyncSession, *, owner_id: int, knowledge_base_id: str) -> PurgeCounts:
    return PurgeCounts().add(
        await delete_source_evidence(
            db,
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            delete_entire_scope=True,
        )
    )


async def purge_owner(db: AsyncSession, *, owner_id: int) -> PurgeCounts:
    scopes: set[str | None] = set(
        await db.scalars(select(CanonicalMemory.knowledge_base_id).where(CanonicalMemory.owner_id == owner_id))
    )
    scopes.update(
        await db.scalars(select(MemoryCandidate.knowledge_base_id).where(MemoryCandidate.owner_id == owner_id))
    )
    scopes.update(await db.scalars(select(Evidence.knowledge_base_id).where(Evidence.owner_id == owner_id)))
    counts = PurgeCounts()
    for knowledge_base_id in sorted(scopes, key=lambda item: item or ""):
        counts = counts.add(
            await delete_source_evidence(
                db,
                owner_id=owner_id,
                knowledge_base_id=knowledge_base_id,
                delete_entire_scope=True,
            )
        )
    return counts


async def consume_purge_confirmation(
    db: AsyncSession,
    *,
    owner_id: int,
    knowledge_base_id: str | None,
    target_id: str,
    actor_id: str,
    reason: str,
    confirmation_jti: str,
) -> None:
    _audit(
        db,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        action="purge",
        target_type="scope",
        target_id=target_id,
        actor_id=actor_id,
        reason=reason,
        confirmation_jti=confirmation_jti,
    )
    # Flush before deletion so the unique constraint atomically rejects replay.
    try:
        await db.flush()
    except IntegrityError:
        raise PurgeConfirmationReplay("purge confirmation was already consumed") from None
