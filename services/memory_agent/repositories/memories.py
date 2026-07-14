from collections.abc import Iterable
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory_agent.models.canonical_memory import CanonicalMemory
from services.memory_agent.models.evidence import candidate_evidence, revision_evidence
from services.memory_agent.models.memory_candidate import MemoryCandidate
from services.memory_agent.models.memory_revision import MemoryRevision


def _scope(model: type[CanonicalMemory] | type[MemoryCandidate], owner_id: int, knowledge_base_id: str | None):
    knowledge_scope = (
        model.knowledge_base_id.is_(None)
        if knowledge_base_id is None
        else model.knowledge_base_id == knowledge_base_id
    )
    return model.owner_id == owner_id, knowledge_scope


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


async def attach_candidate_evidence(
    db: AsyncSession, *, candidate_id: str, evidence_ids: Iterable[str]
) -> None:
    for evidence_id in set(evidence_ids):
        await db.execute(
            insert(candidate_evidence).values(candidate_id=candidate_id, evidence_id=evidence_id)
        )


async def attach_revision_evidence(
    db: AsyncSession, *, revision_id: str, evidence_ids: Iterable[str]
) -> None:
    existing = set(
        await db.scalars(
            select(revision_evidence.c.evidence_id).where(
                revision_evidence.c.revision_id == revision_id
            )
        )
    )
    for evidence_id in set(evidence_ids) - existing:
        await db.execute(
            insert(revision_evidence).values(revision_id=revision_id, evidence_id=evidence_id)
        )


async def candidate_evidence_ids(db: AsyncSession, candidate_id: str) -> list[str]:
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

    historical_fingerprints = list(
        await db.scalars(
            select(MemoryRevision.fingerprint).where(
                MemoryRevision.memory_id == memory_id,
                MemoryRevision.owner_id == owner_id,
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
