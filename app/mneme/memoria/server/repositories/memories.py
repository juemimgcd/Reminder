from collections.abc import Iterable
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete, or_, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.memoria.server.models.canonical_memory import CanonicalMemory
from app.mneme.memoria.server.models.evidence import Evidence, candidate_evidence, revision_evidence
from app.mneme.memoria.server.models.memory_candidate import MemoryCandidate
from app.mneme.memoria.server.models.memory_revision import MemoryRevision


def _scope(model: type[CanonicalMemory] | type[MemoryCandidate], owner_id: int, knowledge_base_id: str | None):
    knowledge_scope = (
        model.knowledge_base_id.is_(None)
        if knowledge_base_id is None
        else model.knowledge_base_id == knowledge_base_id
    )
    return model.owner_id == owner_id, knowledge_scope


def _knowledge_scope(column, knowledge_base_id: str | None):
    return column.is_(None) if knowledge_base_id is None else column == knowledge_base_id


async def lock_memory_slot(db: AsyncSession, lock_key: int) -> None:
    await db.execute(text("SELECT pg_advisory_xact_lock(:lock_key)"), {"lock_key": lock_key})


async def load_candidate_for_update(
    db: AsyncSession,
    *,
    candidate_id: str,
    owner_id: int,
    knowledge_base_id: str | None,
) -> MemoryCandidate | None:
    return await db.scalar(
        select(MemoryCandidate)
        .where(
            MemoryCandidate.candidate_id == candidate_id,
            *_scope(MemoryCandidate, owner_id, knowledge_base_id),
        )
        .with_for_update()
    )


async def load_memory_for_update(
    db: AsyncSession,
    *,
    memory_id: str,
    owner_id: int,
    knowledge_base_id: str | None,
) -> CanonicalMemory | None:
    return await db.scalar(
        select(CanonicalMemory)
        .where(
            CanonicalMemory.memory_id == memory_id,
            *_scope(CanonicalMemory, owner_id, knowledge_base_id),
        )
        .with_for_update()
    )


async def find_active_memory(
    db: AsyncSession,
    *,
    owner_id: int,
    knowledge_base_id: str | None,
    fingerprint: str,
) -> CanonicalMemory | None:
    return await db.scalar(
        select(CanonicalMemory).where(
            *_scope(CanonicalMemory, owner_id, knowledge_base_id),
            CanonicalMemory.fingerprint == fingerprint,
            CanonicalMemory.status == "active",
        ).with_for_update()
    )


async def find_conflicting_memory(
    db: AsyncSession,
    *,
    owner_id: int,
    knowledge_base_id: str | None,
    memory_type: str,
    subject: str,
    predicate: str,
    fingerprint: str,
) -> CanonicalMemory | None:
    return await db.scalar(
        select(CanonicalMemory).where(
            *_scope(CanonicalMemory, owner_id, knowledge_base_id),
            CanonicalMemory.memory_type == memory_type,
            CanonicalMemory.subject == subject,
            CanonicalMemory.predicate == predicate,
            CanonicalMemory.fingerprint != fingerprint,
            CanonicalMemory.status == "active",
        ).with_for_update()
    )


async def load_active_revision(
    db: AsyncSession,
    *,
    memory: CanonicalMemory,
    owner_id: int,
    knowledge_base_id: str | None,
) -> MemoryRevision:
    if memory.active_revision_id is None:
        raise ValueError("canonical memory has no active revision")
    revision = await db.scalar(
        select(MemoryRevision)
        .where(
            MemoryRevision.revision_id == memory.active_revision_id,
            MemoryRevision.memory_id == memory.memory_id,
            MemoryRevision.owner_id == owner_id,
            _knowledge_scope(MemoryRevision.knowledge_base_id, knowledge_base_id),
            MemoryRevision.valid_to.is_(None),
        )
        .with_for_update()
    )
    if revision is None:
        raise ValueError("active revision is missing, closed, or outside owner scope")
    return revision


async def validate_evidence_scope(
    db: AsyncSession,
    *,
    evidence_ids: Iterable[str],
    owner_id: int,
    knowledge_base_id: str | None,
) -> set[str]:
    requested = set(evidence_ids)
    if not requested:
        return set()
    scoped = set(
        await db.scalars(
            select(Evidence.evidence_id).where(
                Evidence.evidence_id.in_(requested),
                Evidence.owner_id == owner_id,
                _knowledge_scope(Evidence.knowledge_base_id, knowledge_base_id),
            )
        )
    )
    if scoped != requested:
        raise ValueError("evidence is missing or outside owner scope")
    return scoped


async def attach_candidate_evidence(
    db: AsyncSession,
    *,
    candidate_id: str,
    evidence_ids: Iterable[str],
    owner_id: int,
    knowledge_base_id: str | None,
) -> int:
    candidate = await load_candidate_for_update(
        db,
        candidate_id=candidate_id,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
    )
    if candidate is None:
        raise ValueError("candidate is missing or outside owner scope")
    scoped_ids = await validate_evidence_scope(
        db,
        evidence_ids=evidence_ids,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
    )
    attached = 0
    for evidence_id in scoped_ids:
        result = await db.execute(
            insert(candidate_evidence)
            .values(candidate_id=candidate_id, evidence_id=evidence_id)
            .on_conflict_do_nothing()
            .returning(candidate_evidence.c.evidence_id)
        )
        attached += result.scalar_one_or_none() is not None
    return attached


async def attach_revision_evidence(
    db: AsyncSession,
    *,
    revision_id: str,
    evidence_ids: Iterable[str],
    owner_id: int,
    knowledge_base_id: str | None,
) -> int:
    revision = await db.scalar(
        select(MemoryRevision)
        .where(
            MemoryRevision.revision_id == revision_id,
            MemoryRevision.owner_id == owner_id,
            _knowledge_scope(MemoryRevision.knowledge_base_id, knowledge_base_id),
        )
        .with_for_update()
    )
    if revision is None:
        raise ValueError("revision is missing or outside owner scope")
    scoped_ids = await validate_evidence_scope(
        db,
        evidence_ids=evidence_ids,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
    )
    attached = 0
    for evidence_id in scoped_ids:
        result = await db.execute(
            insert(revision_evidence)
            .values(revision_id=revision_id, evidence_id=evidence_id)
            .on_conflict_do_nothing()
            .returning(revision_evidence.c.evidence_id)
        )
        attached += result.scalar_one_or_none() is not None
    return attached


async def candidate_evidence_ids(
    db: AsyncSession,
    *,
    candidate_id: str,
    owner_id: int,
    knowledge_base_id: str | None,
) -> list[str]:
    candidate = await load_candidate_for_update(
        db,
        candidate_id=candidate_id,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
    )
    if candidate is None:
        raise ValueError("candidate is missing or outside owner scope")
    return list(
        await db.scalars(
            select(candidate_evidence.c.evidence_id).where(
                candidate_evidence.c.candidate_id == candidate_id
            )
        )
    )


async def hard_delete_memory(
    db: AsyncSession,
    *,
    memory_id: str,
    owner_id: int,
    knowledge_base_id: str | None,
) -> bool:
    memory = await load_memory_for_update(
        db,
        memory_id=memory_id,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
    )
    if memory is None:
        return False
    await load_active_revision(
        db,
        memory=memory,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
    )

    historical_fingerprints = list(
        await db.scalars(
            select(MemoryRevision.fingerprint).where(
                MemoryRevision.memory_id == memory_id,
                MemoryRevision.owner_id == owner_id,
                _knowledge_scope(MemoryRevision.knowledge_base_id, knowledge_base_id),
            )
        )
    )
    await db.execute(
        delete(MemoryCandidate).where(
            *_scope(MemoryCandidate, owner_id, knowledge_base_id),
            or_(
                MemoryCandidate.conflicting_memory_id == memory_id,
                MemoryCandidate.fingerprint.in_(historical_fingerprints),
            ),
        )
    )
    await db.delete(memory)
    await db.flush()
    return True


def new_id() -> str:
    return uuid4().hex


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
