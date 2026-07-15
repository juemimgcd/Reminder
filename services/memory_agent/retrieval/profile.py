from services.memory_agent.retrieval.contracts import RetrievedEvidence
from services.memory_agent.retrieval.memories import MemoryRetriever

PROFILE_MEMORY_TYPES = ("profile_fact", "preference", "goal", "constraint")


class ProfileRetriever:
    def __init__(self, memories: MemoryRetriever | None = None) -> None:
        self._memories = memories or MemoryRetriever()

    async def search(
        self,
        *,
        owner_id: int,
        knowledge_base_id: str | None,
        query: str,
        top_k: int,
    ) -> list[RetrievedEvidence]:
        return await self._memories.search(
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            query=query,
            top_k=top_k,
            temporal_scope="current",
            memory_types=PROFILE_MEMORY_TYPES,
            evidence_type="profile",
        )
