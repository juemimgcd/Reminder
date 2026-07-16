from app.mneme.memoria.server.database import open_read_session
from app.mneme.memoria.server.retrieval.contracts import RetrievalScope, RetrievedEvidence
from app.mneme.memoria.server.retrieval.fusion import reciprocal_rank_fusion
from app.mneme.memoria.server.retrieval.keyword import search_keyword
from app.mneme.memoria.server.retrieval.vector import search_vector


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
