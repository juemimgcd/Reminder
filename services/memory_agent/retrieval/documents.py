from services.memory_agent.database import open_read_session
from services.memory_agent.retrieval.contracts import RetrievalScope, RetrievedEvidence
from services.memory_agent.retrieval.fusion import reciprocal_rank_fusion
from services.memory_agent.retrieval.keyword import search_keyword
from services.memory_agent.retrieval.vector import search_vector


class DocumentRetriever:
    async def search(
        self,
        scope: RetrievalScope,
        query: str,
        top_k: int,
    ) -> list[RetrievedEvidence]:
        if top_k <= 0:
            return []

        async with open_read_session() as db:
            vector_hits = await search_vector(db, scope=scope, query=query, limit=top_k)
            keyword_hits = await search_keyword(db, scope=scope, query=query, limit=top_k)
        return reciprocal_rank_fusion((vector_hits, keyword_hits), top_k=top_k)
