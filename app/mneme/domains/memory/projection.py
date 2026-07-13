from sqlalchemy import delete, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.crud.memory_entry import list_memory_entries_by_knowledge_base_id
from app.mneme.domains.memory.governance import build_memory_governance_view
from app.mneme.models.memory import (
    CanonicalMemory,
    MemoryEntry,
    MemoryRelation,
    canonical_memory_evidence,
)
from app.mneme.schemas.memory_governance import MemoryGovernanceData


async def rebuild_memory_governance_projection(
    db: AsyncSession,
    *,
    user_id: int,
    knowledge_base_id: str,
    knowledge_base_pk: int,
    entries: list[MemoryEntry] | None = None,
) -> MemoryGovernanceData:
    active_entries = entries
    if active_entries is None:
        active_entries = await list_memory_entries_by_knowledge_base_id(
            db,
            knowledge_base_id=knowledge_base_id,
        )

    governance = build_memory_governance_view(
        knowledge_base_id=knowledge_base_id,
        entries=active_entries,
    )

    await db.execute(delete(MemoryRelation).where(MemoryRelation.knowledge_base_pk == knowledge_base_pk))
    await db.execute(delete(CanonicalMemory).where(CanonicalMemory.knowledge_base_pk == knowledge_base_pk))

    canonical_rows = [
        CanonicalMemory(
            id=item.canonical_id,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            knowledge_base_pk=knowledge_base_pk,
            entry_name=item.entry_name,
            entry_type=item.entry_type,
            summary=item.summary,
            representative_entry_id=item.representative_entry_id,
            evidence_count=item.evidence_count,
            document_count=item.document_count,
            importance_score=item.importance_score,
            status=item.status,
            first_seen_at=item.first_seen_at,
            last_seen_at=item.last_seen_at,
        )
        for item in governance.canonical_memories
    ]
    db.add_all(canonical_rows)
    await db.flush()

    evidence_rows = [
        {
            "canonical_memory_id": item.canonical_id,
            "memory_entry_id": entry_id,
        }
        for item in governance.canonical_memories
        for entry_id in item.entry_ids
    ]
    if evidence_rows:
        await db.execute(insert(canonical_memory_evidence), evidence_rows)

    db.add_all(
        [
            MemoryRelation(
                id=item.relation_id,
                knowledge_base_id=knowledge_base_id,
                knowledge_base_pk=knowledge_base_pk,
                source_entry_id=item.source_entry_id,
                target_entry_id=item.target_entry_id,
                relation_type=item.relation_type,
                confidence=item.confidence,
                reason=item.reason,
            )
            for item in governance.relations
        ]
    )
    await db.flush()
    return governance
