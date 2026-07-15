from sqlalchemy import func, or_, select
from sqlalchemy.orm import aliased

from services.memory_agent.database import open_read_session
from services.memory_agent.models.canonical_memory import CanonicalMemory
from services.memory_agent.models.memory_relation import MemoryRelation
from services.memory_agent.models.memory_revision import MemoryRevision
from services.memory_agent.retrieval.contracts import RetrievedEvidence


class RelationRetriever:
    async def search(
        self,
        *,
        owner_id: int,
        knowledge_base_id: str | None,
        query: str,
        top_k: int,
    ) -> list[RetrievedEvidence]:
        if top_k <= 0:
            return []

        source_memory = aliased(CanonicalMemory)
        target_memory = aliased(CanonicalMemory)
        source_revision = aliased(MemoryRevision)
        target_revision = aliased(MemoryRevision)
        scope_filters = [
            MemoryRelation.owner_id == owner_id,
            source_memory.owner_id == owner_id,
            target_memory.owner_id == owner_id,
            source_revision.owner_id == owner_id,
            target_revision.owner_id == owner_id,
        ]
        scoped_models = (MemoryRelation, source_memory, target_memory, source_revision, target_revision)
        for model in scoped_models:
            column = model.knowledge_base_id
            scope_filters.append(
                column.is_(None) if knowledge_base_id is None else column == knowledge_base_id
            )

        now = func.now()
        source_text = func.concat_ws(
            " ", source_revision.subject, source_revision.predicate, source_revision.value
        )
        target_text = func.concat_ws(
            " ", target_revision.subject, target_revision.predicate, target_revision.value
        )
        relevance = func.concat_ws(" ", source_text, MemoryRelation.relation_type, target_text).ilike(
            f"%{query.strip()}%"
        )
        statement = (
            select(
                MemoryRelation.relation_id,
                MemoryRelation.relation_type,
                source_memory.memory_id.label("source_memory_id"),
                target_memory.memory_id.label("target_memory_id"),
                source_revision.subject.label("source_subject"),
                source_revision.predicate.label("source_predicate"),
                source_revision.value.label("source_value"),
                target_revision.subject.label("target_subject"),
                target_revision.predicate.label("target_predicate"),
                target_revision.value.label("target_value"),
                MemoryRelation.created_at,
            )
            .join(source_memory, source_memory.memory_id == MemoryRelation.source_memory_id)
            .join(target_memory, target_memory.memory_id == MemoryRelation.target_memory_id)
            .join(source_revision, source_revision.revision_id == source_memory.active_revision_id)
            .join(target_revision, target_revision.revision_id == target_memory.active_revision_id)
            .where(
                *scope_filters,
                source_memory.status == "active",
                target_memory.status == "active",
                source_revision.valid_from <= now,
                target_revision.valid_from <= now,
                or_(source_revision.valid_to.is_(None), source_revision.valid_to > now),
                or_(target_revision.valid_to.is_(None), target_revision.valid_to > now),
            )
            .order_by(relevance.desc(), MemoryRelation.created_at.desc(), MemoryRelation.relation_id.asc())
            .limit(top_k)
        )
        async with open_read_session() as db:
            rows = (await db.execute(statement)).mappings().all()

        return [
            RetrievedEvidence(
                evidence_id=f"relation:{row['relation_id']}",
                source_type="relation",
                source_id=row["relation_id"],
                content=(
                    f"{row['source_subject']} {row['source_predicate']} {row['source_value']} "
                    f"--{row['relation_type']}--> "
                    f"{row['target_subject']} {row['target_predicate']} {row['target_value']}"
                ),
                score=1.0,
                metadata={
                    "relation_type": row["relation_type"],
                    "source_memory_id": row["source_memory_id"],
                    "target_memory_id": row["target_memory_id"],
                    "created_at": row["created_at"].isoformat(),
                },
            )
            for row in rows
        ]
