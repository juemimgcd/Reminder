from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory_agent.memory.identity import memory_fingerprint, normalize_memory_text
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
    load_candidate_for_update,
    load_memory_for_update,
    new_id,
    utc_now,
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
        evidence = await db.scalar(
            select(Evidence).where(
                Evidence.owner_id == owner_id,
                Evidence.knowledge_base_id.is_(None)
                if knowledge_base_id is None
                else Evidence.knowledge_base_id == knowledge_base_id,
                Evidence.source_type == item.source_type,
                Evidence.source_id == item.source_id,
                Evidence.source_version == item.source_version,
                Evidence.content_hash == item.content_hash,
            )
        )
        if evidence is None:
            evidence = Evidence(
                evidence_id=new_id(),
                owner_id=owner_id,
                knowledge_base_id=knowledge_base_id,
                source_type=item.source_type,
                source_id=item.source_id,
                source_version=item.source_version,
                minimum_text=item.minimum_text,
                content_hash=item.content_hash,
                occurred_at=item.occurred_at,
            )
            db.add(evidence)
            await db.flush()
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
    memory = CanonicalMemory(
        memory_id=new_id(),
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        memory_type=memory_type,
        subject=subject,
        predicate=predicate,
        value=value,
        fingerprint=fingerprint,
        confidence=confidence,
        status="active",
    )
    db.add(memory)
    await db.flush()
    revision = MemoryRevision(
        revision_id=new_id(),
        memory_id=memory.memory_id,
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
    await attach_revision_evidence(db, revision_id=revision.revision_id, evidence_ids=evidence_ids)
    memory.active_revision_id = revision.revision_id
    await db.flush()
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
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")

    # Secrets are rejected before normalization, evidence creation, or any ORM row construction.
    if classify_candidate(
        sensitivity=sensitivity,
        confidence=confidence,
        explicit_request=explicit_request,
    ) == "reject":
        return ReconciliationResult(decision="reject")
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
    compatible = await find_active_memory(
        db,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        fingerprint=fingerprint,
    )
    stored_evidence = await _persist_evidence(
        db,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        inputs=evidence or [],
    )
    evidence_ids = [item.evidence_id for item in stored_evidence]
    if compatible is not None:
        compatible.confidence = _combined_confidence(compatible.confidence, confidence)
        if compatible.active_revision_id is None:
            raise ValueError("canonical memory has no active revision")
        await attach_revision_evidence(
            db, revision_id=compatible.active_revision_id, evidence_ids=evidence_ids
        )
        await db.flush()
        return ReconciliationResult(
            decision="promote", memory=compatible, reinforced=True
        )

    conflict = await find_conflicting_memory(
        db,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        memory_type=memory_type,
        subject=normalized_subject,
        predicate=normalized_predicate,
        fingerprint=fingerprint,
    )
    decision = classify_candidate(
        sensitivity=sensitivity,
        confidence=confidence,
        explicit_request=explicit_request,
        has_conflict=conflict is not None,
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
        decided_at=utc_now() if decision == "promote" else None,
    )
    db.add(candidate)
    await db.flush()
    await attach_candidate_evidence(db, candidate_id=candidate.candidate_id, evidence_ids=evidence_ids)
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
    memory = await load_memory_for_update(
        db,
        memory_id=memory_id,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
    )
    if memory is None:
        raise LookupError("memory not found in owner scope")
    if memory.active_revision_id is None:
        raise ValueError("canonical memory has no active revision")
    old_revision = await db.scalar(
        select(MemoryRevision)
        .where(
            MemoryRevision.revision_id == memory.active_revision_id,
            MemoryRevision.owner_id == owner_id,
            MemoryRevision.knowledge_base_id.is_(None)
            if knowledge_base_id is None
            else MemoryRevision.knowledge_base_id == knowledge_base_id,
        )
        .with_for_update()
    )
    if old_revision is None:
        raise ValueError("active revision not found in owner scope")

    now = utc_now()
    old_revision.valid_to = now
    normalized_subject = normalize_memory_text(subject)
    normalized_predicate = normalize_memory_text(predicate)
    normalized_value = normalize_memory_text(value)
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
    await attach_revision_evidence(db, revision_id=revision.revision_id, evidence_ids=evidence_ids or [])
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
    evidence_ids = await candidate_evidence_ids(db, candidate.candidate_id)
    if candidate.conflicting_memory_id is not None:
        memory = await revise_memory(
            db,
            memory_id=candidate.conflicting_memory_id,
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
