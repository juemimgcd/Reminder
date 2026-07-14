from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory_agent.memory.identity import (
    evidence_identity,
    memory_fingerprint,
    memory_slot_lock_key,
    normalize_memory_text,
)
from services.memory_agent.memory.policy import PolicyDecision, classify_candidate
from services.memory_agent.models.canonical_memory import CanonicalMemory
from services.memory_agent.models.evidence import Evidence
from services.memory_agent.models.memory_candidate import (
    MEMORY_TYPES,
    MemoryCandidate,
    MemoryType,
    Sensitivity,
)
from services.memory_agent.models.memory_revision import MemoryRevision
from services.memory_agent.repositories.memories import (
    attach_candidate_evidence,
    attach_revision_evidence,
    candidate_evidence_ids,
    find_active_memory,
    find_conflicting_memory,
    load_active_revision,
    load_candidate_for_update,
    load_memory_for_update,
    lock_memory_slot,
    new_id,
    utc_now,
    validate_evidence_scope,
)


@dataclass(frozen=True)
class EvidenceInput:
    source_type: str
    source_id: str
    source_version: str
    minimum_text: str
    content_hash: str
    occurred_at: datetime


@dataclass(frozen=True)
class ReconciliationResult:
    decision: PolicyDecision
    candidate: MemoryCandidate | None = None
    memory: CanonicalMemory | None = None
    reinforced: bool = False


async def _persist_evidence(
    db: AsyncSession,
    *,
    owner_id: int,
    knowledge_base_id: str | None,
    inputs: list[EvidenceInput],
) -> list[Evidence]:
    stored: list[Evidence] = []
    for item in inputs:
        identity_hash = evidence_identity(
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            source_type=item.source_type,
            source_id=item.source_id,
            source_version=item.source_version,
            content_hash=item.content_hash,
        )
        await db.execute(
            insert(Evidence)
            .values(
                evidence_id=new_id(),
                identity_hash=identity_hash,
                owner_id=owner_id,
                knowledge_base_id=knowledge_base_id,
                source_type=item.source_type,
                source_id=item.source_id,
                source_version=item.source_version,
                minimum_text=item.minimum_text,
                content_hash=item.content_hash,
                occurred_at=item.occurred_at,
            )
            .on_conflict_do_nothing(index_elements=[Evidence.identity_hash])
        )
        evidence = await db.scalar(
            select(Evidence).where(
                Evidence.identity_hash == identity_hash,
                Evidence.owner_id == owner_id,
            )
        )
        if evidence is None:
            raise RuntimeError("evidence upsert did not return a durable row")
        if evidence.knowledge_base_id != knowledge_base_id:
            raise ValueError("evidence identity resolved outside owner scope")
        stored.append(evidence)
    return stored


def _combined_confidence(current: float, additional: float) -> float:
    return min(1.0, 1.0 - ((1.0 - current) * (1.0 - additional)))


async def _create_memory(
    db: AsyncSession,
    *,
    owner_id: int,
    knowledge_base_id: str | None,
    memory_type: MemoryType,
    subject: str,
    predicate: str,
    value: str,
    fingerprint: str,
    confidence: float,
    reason: str,
    actor: str,
    evidence_ids: list[str],
) -> CanonicalMemory:
    memory_id = new_id()
    revision_id = new_id()
    memory = CanonicalMemory(
        memory_id=memory_id,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        memory_type=memory_type,
        subject=subject,
        predicate=predicate,
        value=value,
        fingerprint=fingerprint,
        confidence=confidence,
        status="active",
        active_revision_id=revision_id,
    )
    db.add(memory)
    await db.flush()
    revision = MemoryRevision(
        revision_id=revision_id,
        memory_id=memory_id,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        subject=subject,
        predicate=predicate,
        value=value,
        fingerprint=fingerprint,
        reason=reason,
        actor=actor,
    )
    db.add(revision)
    await db.flush()
    await attach_revision_evidence(
        db,
        revision_id=revision.revision_id,
        evidence_ids=evidence_ids,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
    )
    return memory


async def reconcile_candidate(
    db: AsyncSession,
    *,
    owner_id: int,
    knowledge_base_id: str | None,
    memory_type: MemoryType,
    subject: str,
    predicate: str,
    value: str,
    confidence: float,
    sensitivity: Sensitivity,
    evidence: list[EvidenceInput] | None = None,
    extraction_provenance: dict[str, Any] | None = None,
    explicit_request: bool = False,
    actor: str = "memory-policy",
) -> ReconciliationResult:
    # Secret policy has absolute precedence, including over malformed confidence.
    preliminary_decision = classify_candidate(
        sensitivity=sensitivity,
        confidence=confidence,
        explicit_request=explicit_request,
    )
    if preliminary_decision == "reject":
        return ReconciliationResult(decision="reject")
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")
    if memory_type not in MEMORY_TYPES:
        raise ValueError("unsupported memory type")

    normalized_subject = normalize_memory_text(subject)
    normalized_predicate = normalize_memory_text(predicate)
    normalized_value = normalize_memory_text(value)
    fingerprint = memory_fingerprint(
        subject=normalized_subject,
        predicate=normalized_predicate,
        value=normalized_value,
    )
    await lock_memory_slot(
        db,
        memory_slot_lock_key(
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            memory_type=memory_type,
            subject=normalized_subject,
            predicate=normalized_predicate,
        ),
    )
    compatible = await find_active_memory(
        db,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        fingerprint=fingerprint,
    )
    compatible_revision = None
    if compatible is not None:
        compatible_revision = await load_active_revision(
            db,
            memory=compatible,
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
        )
    conflict = None
    conflict_revision = None
    if compatible is None:
        conflict = await find_conflicting_memory(
            db,
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            memory_type=memory_type,
            subject=normalized_subject,
            predicate=normalized_predicate,
            fingerprint=fingerprint,
        )
        if conflict is not None:
            conflict_revision = await load_active_revision(
                db,
                memory=conflict,
                owner_id=owner_id,
                knowledge_base_id=knowledge_base_id,
            )
    decision = classify_candidate(
        sensitivity=sensitivity,
        confidence=confidence,
        explicit_request=explicit_request,
        has_conflict=conflict is not None,
    )
    stored_evidence = await _persist_evidence(
        db,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        inputs=evidence or [],
    )
    evidence_ids = [item.evidence_id for item in stored_evidence]

    if decision == "promote" and compatible is not None:
        if compatible_revision is None:
            raise ValueError("canonical memory has no active revision")
        attached = await attach_revision_evidence(
            db,
            revision_id=compatible_revision.revision_id,
            evidence_ids=evidence_ids,
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
        )
        if attached:
            compatible.confidence = _combined_confidence(compatible.confidence, confidence)
            await db.flush()
        return ReconciliationResult(
            decision="promote",
            memory=compatible,
            reinforced=attached > 0,
        )

    candidate = MemoryCandidate(
        candidate_id=new_id(),
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        memory_type=memory_type,
        subject=normalized_subject,
        predicate=normalized_predicate,
        value=normalized_value,
        fingerprint=fingerprint,
        confidence=confidence,
        sensitivity=sensitivity,
        status="promoted" if decision == "promote" else "pending",
        extraction_provenance=extraction_provenance or {},
        conflicting_memory_id=conflict.memory_id if conflict is not None else None,
        conflicting_revision_id=(
            conflict_revision.revision_id if conflict_revision is not None else None
        ),
        decided_at=utc_now() if decision == "promote" else None,
    )
    db.add(candidate)
    await db.flush()
    await attach_candidate_evidence(
        db,
        candidate_id=candidate.candidate_id,
        evidence_ids=evidence_ids,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
    )
    if decision == "pending":
        return ReconciliationResult(decision=decision, candidate=candidate)

    if conflict is not None:
        memory = await revise_memory(
            db,
            memory_id=conflict.memory_id,
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            subject=normalized_subject,
            predicate=normalized_predicate,
            value=normalized_value,
            confidence=confidence,
            reason="explicit_request_replacement",
            actor=actor,
            evidence_ids=evidence_ids,
            sensitivity=sensitivity,
        )
    else:
        memory = await _create_memory(
            db,
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            memory_type=memory_type,
            subject=normalized_subject,
            predicate=normalized_predicate,
            value=normalized_value,
            fingerprint=fingerprint,
            confidence=confidence,
            reason="explicit_request" if explicit_request else "automatic_promotion",
            actor=actor,
            evidence_ids=evidence_ids,
        )
    return ReconciliationResult(decision=decision, candidate=candidate, memory=memory)


async def revise_memory(
    db: AsyncSession,
    *,
    memory_id: str,
    owner_id: int,
    knowledge_base_id: str | None,
    subject: str,
    predicate: str,
    value: str,
    reason: str,
    actor: str,
    evidence_ids: list[str] | None = None,
    confidence: float | None = None,
    sensitivity: Sensitivity = "low",
) -> CanonicalMemory:
    if sensitivity == "secret":
        raise ValueError("secret values cannot be persisted as memory")
    if confidence is not None and not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")
    normalized_subject = normalize_memory_text(subject)
    normalized_predicate = normalize_memory_text(predicate)
    normalized_value = normalize_memory_text(value)
    scoped_memory = await db.scalar(
        select(CanonicalMemory).where(
            CanonicalMemory.memory_id == memory_id,
            CanonicalMemory.owner_id == owner_id,
            CanonicalMemory.knowledge_base_id.is_(None)
            if knowledge_base_id is None
            else CanonicalMemory.knowledge_base_id == knowledge_base_id,
        )
    )
    if scoped_memory is None:
        raise LookupError("memory not found in owner scope")
    await lock_memory_slot(
        db,
        memory_slot_lock_key(
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            memory_type=scoped_memory.memory_type,
            subject=normalized_subject,
            predicate=normalized_predicate,
        ),
    )
    memory = await load_memory_for_update(
        db,
        memory_id=memory_id,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
    )
    if memory is None:
        raise LookupError("memory not found in owner scope")
    old_revision = await load_active_revision(
        db,
        memory=memory,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
    )
    scoped_evidence_ids = await validate_evidence_scope(
        db,
        evidence_ids=evidence_ids or [],
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
    )

    now = utc_now()
    old_revision.valid_to = now
    await db.flush()
    fingerprint = memory_fingerprint(
        subject=normalized_subject, predicate=normalized_predicate, value=normalized_value
    )
    revision = MemoryRevision(
        revision_id=new_id(),
        memory_id=memory.memory_id,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        subject=normalized_subject,
        predicate=normalized_predicate,
        value=normalized_value,
        fingerprint=fingerprint,
        valid_from=now,
        reason=reason,
        actor=actor,
    )
    db.add(revision)
    await db.flush()
    await attach_revision_evidence(
        db,
        revision_id=revision.revision_id,
        evidence_ids=scoped_evidence_ids,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
    )
    memory.subject = normalized_subject
    memory.predicate = normalized_predicate
    memory.value = normalized_value
    memory.fingerprint = fingerprint
    memory.active_revision_id = revision.revision_id
    memory.status = "active"
    if confidence is not None:
        memory.confidence = confidence
    await db.flush()
    return memory


async def confirm_candidate(
    db: AsyncSession,
    *,
    candidate_id: str,
    owner_id: int,
    knowledge_base_id: str | None,
    actor: str,
) -> CanonicalMemory:
    candidate = await load_candidate_for_update(
        db,
        candidate_id=candidate_id,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
    )
    if candidate is None:
        raise LookupError("candidate not found in owner scope")
    if candidate.status != "pending":
        raise ValueError("only pending candidates can be confirmed")
    if candidate.sensitivity == "secret":
        raise ValueError("secret candidates cannot be confirmed")
    await lock_memory_slot(
        db,
        memory_slot_lock_key(
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            memory_type=candidate.memory_type,
            subject=candidate.subject,
            predicate=candidate.predicate,
        ),
    )
    evidence_ids = await candidate_evidence_ids(
        db,
        candidate_id=candidate.candidate_id,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
    )
    compatible = await find_active_memory(
        db,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        fingerprint=candidate.fingerprint,
    )
    if compatible is not None:
        active_revision = await load_active_revision(
            db,
            memory=compatible,
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
        )
        attached = await attach_revision_evidence(
            db,
            revision_id=active_revision.revision_id,
            evidence_ids=evidence_ids,
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
        )
        if attached:
            compatible.confidence = _combined_confidence(
                compatible.confidence, candidate.confidence
            )
        memory = compatible
    else:
        current_conflict = await find_conflicting_memory(
            db,
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            memory_type=candidate.memory_type,
            subject=candidate.subject,
            predicate=candidate.predicate,
            fingerprint=candidate.fingerprint,
        )
        if current_conflict is not None:
            current_revision = await load_active_revision(
                db,
                memory=current_conflict,
                owner_id=owner_id,
                knowledge_base_id=knowledge_base_id,
            )
            if (
                candidate.conflicting_memory_id != current_conflict.memory_id
                or candidate.conflicting_revision_id != current_revision.revision_id
            ):
                raise ValueError(
                    "candidate is stale because the current memory changed; re-review is required"
                )
            memory = await revise_memory(
                db,
                memory_id=current_conflict.memory_id,
                owner_id=owner_id,
                knowledge_base_id=knowledge_base_id,
                subject=candidate.subject,
                predicate=candidate.predicate,
                value=candidate.value,
                confidence=candidate.confidence,
                reason="confirmed_replacement",
                actor=actor,
                evidence_ids=evidence_ids,
                sensitivity=candidate.sensitivity,
            )
        else:
            memory = await _create_memory(
                db,
                owner_id=owner_id,
                knowledge_base_id=knowledge_base_id,
                memory_type=candidate.memory_type,
                subject=candidate.subject,
                predicate=candidate.predicate,
                value=candidate.value,
                fingerprint=candidate.fingerprint,
                confidence=candidate.confidence,
                reason="user_confirmation",
                actor=actor,
                evidence_ids=evidence_ids,
            )
    candidate.status = "promoted"
    candidate.decided_at = utc_now()
    await db.flush()
    return memory


async def reject_candidate(
    db: AsyncSession,
    *,
    candidate_id: str,
    owner_id: int,
    knowledge_base_id: str | None,
) -> MemoryCandidate:
    candidate = await load_candidate_for_update(
        db,
        candidate_id=candidate_id,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
    )
    if candidate is None:
        raise LookupError("candidate not found in owner scope")
    if candidate.status != "pending":
        raise ValueError("only pending candidates can be rejected")
    candidate.status = "rejected"
    candidate.decided_at = utc_now()
    await db.flush()
    return candidate
