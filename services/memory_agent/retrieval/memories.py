from datetime import datetime
from typing import Literal

from sqlalchemy import and_, func, or_, select

from services.memory_agent.database import open_read_session
from services.memory_agent.models.canonical_memory import CanonicalMemory
from services.memory_agent.models.memory_revision import MemoryRevision
from services.memory_agent.retrieval.contracts import RetrievedEvidence

TemporalScope = Literal["current", "history"]


def _knowledge_base_clause(knowledge_base_id: str | None):
    if knowledge_base_id is None:
        return CanonicalMemory.knowledge_base_id.is_(None)
    return CanonicalMemory.knowledge_base_id == knowledge_base_id


class MemoryRetriever:
    async def search(
        self,
        *,
        owner_id: int,
        knowledge_base_id: str | None,
        query: str,
        top_k: int,
        temporal_scope: TemporalScope = "current",
        memory_types: tuple[str, ...] | None = None,
        excluded_memory_types: tuple[str, ...] | None = None,
        evidence_type: Literal["memory", "profile"] = "memory",
    ) -> list[RetrievedEvidence]:
        if top_k <= 0:
            return []

        now = func.now()
        text_value = func.concat_ws(
            " ",
            MemoryRevision.subject,
            MemoryRevision.predicate,
            MemoryRevision.value,
        )
        filters = [
            CanonicalMemory.owner_id == owner_id,
            _knowledge_base_clause(knowledge_base_id),
            MemoryRevision.owner_id == owner_id,
            (
                MemoryRevision.knowledge_base_id.is_(None)
                if knowledge_base_id is None
                else MemoryRevision.knowledge_base_id == knowledge_base_id
            ),
            MemoryRevision.valid_from <= now,
        ]
        if temporal_scope == "current":
            filters.extend(
                [
                    CanonicalMemory.status == "active",
                    CanonicalMemory.active_revision_id == MemoryRevision.revision_id,
                    or_(MemoryRevision.valid_to.is_(None), MemoryRevision.valid_to > now),
                ]
            )
        if memory_types:
            filters.append(CanonicalMemory.memory_type.in_(memory_types))
        if excluded_memory_types:
            filters.append(CanonicalMemory.memory_type.not_in(excluded_memory_types))

        pattern = f"%{query.strip()}%"
        relevance = text_value.ilike(pattern)
        statement = (
            select(
                CanonicalMemory.memory_id,
                CanonicalMemory.memory_type,
                CanonicalMemory.confidence,
                MemoryRevision.revision_id,
                MemoryRevision.subject,
                MemoryRevision.predicate,
                MemoryRevision.value,
                MemoryRevision.valid_from,
                MemoryRevision.valid_to,
            )
            .join(MemoryRevision, MemoryRevision.memory_id == CanonicalMemory.memory_id)
            .where(and_(*filters))
            .order_by(relevance.desc(), CanonicalMemory.confidence.desc(), MemoryRevision.valid_from.desc())
            .limit(top_k)
        )
        async with open_read_session() as db:
            rows = (await db.execute(statement)).mappings().all()

        return [
            RetrievedEvidence(
                evidence_id=f"{evidence_type}:{row['revision_id']}",
                source_type=evidence_type,
                source_id=row["memory_id"],
                content=f"{row['subject']} {row['predicate']} {row['value']}",
                score=float(row["confidence"]),
                metadata={
                    "memory_type": row["memory_type"],
                    "valid_from": _isoformat(row["valid_from"]),
                    "valid_to": _isoformat(row["valid_to"]),
                },
            )
            for row in rows
        ]


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
