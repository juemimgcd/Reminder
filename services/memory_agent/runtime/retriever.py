from collections.abc import Callable

from services.memory_agent.retrieval.contracts import RetrievalScope, RetrievedEvidence
from services.memory_agent.retrieval.documents import DocumentRetriever
from services.memory_agent.retrieval.memories import MemoryRetriever
from services.memory_agent.retrieval.profile import PROFILE_MEMORY_TYPES, ProfileRetriever
from services.memory_agent.retrieval.relations import RelationRetriever
from services.memory_agent.runtime.contracts import RetrievalRequest


class ScopedEvidenceRetriever:
    def __init__(
        self,
        *,
        documents_factory: Callable[[], DocumentRetriever] = DocumentRetriever,
        memories_factory: Callable[[], MemoryRetriever] = MemoryRetriever,
        profile_factory: Callable[[], ProfileRetriever] = ProfileRetriever,
        relations_factory: Callable[[], RelationRetriever] = RelationRetriever,
    ) -> None:
        self._documents_factory = documents_factory
        self._memories_factory = memories_factory
        self._profile_factory = profile_factory
        self._relations_factory = relations_factory

    async def retrieve(self, request: RetrievalRequest) -> list[RetrievedEvidence]:
        if not request.plan.uses_private_sources:
            return []

        results: list[RetrievedEvidence] = []
        if request.plan.document:
            if request.knowledge_base_id is None:
                raise ValueError("document retrieval requires a knowledge base scope")
            results.extend(
                await self._documents_factory().search(
                    RetrievalScope(
                        owner_id=request.owner_id,
                        knowledge_base_id=request.knowledge_base_id,
                    ),
                    request.question,
                    request.top_k,
                )
            )
        if request.plan.memory:
            results.extend(
                await self._memories_factory().search(
                    owner_id=request.owner_id,
                    knowledge_base_id=request.knowledge_base_id,
                    query=request.question,
                    top_k=request.top_k,
                    temporal_scope=request.temporal_scope,
                    excluded_memory_types=PROFILE_MEMORY_TYPES if request.plan.profile else None,
                )
            )
        if request.plan.profile:
            results.extend(
                await self._profile_factory().search(
                    owner_id=request.owner_id,
                    knowledge_base_id=request.knowledge_base_id,
                    query=request.question,
                    top_k=request.top_k,
                )
            )
        if request.plan.relations:
            results.extend(
                await self._relations_factory().search(
                    owner_id=request.owner_id,
                    knowledge_base_id=request.knowledge_base_id,
                    query=request.question,
                    top_k=request.top_k,
                )
            )

        unique = {item.evidence_id: item for item in results}
        return sorted(unique.values(), key=lambda item: (-item.score, item.evidence_id))[
            : request.top_k
        ]
