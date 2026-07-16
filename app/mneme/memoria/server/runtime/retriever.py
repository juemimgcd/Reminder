import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.mneme.memoria.server.observability.context import safe_log
from app.mneme.memoria.server.retrieval.contracts import RetrievalScope, RetrievedEvidence
from app.mneme.memoria.server.retrieval.documents import DocumentRetriever
from app.mneme.memoria.server.retrieval.memories import MemoryRetriever
from app.mneme.memoria.server.retrieval.profile import PROFILE_MEMORY_TYPES, ProfileRetriever
from app.mneme.memoria.server.retrieval.relations import RelationRetriever
from app.mneme.memoria.server.runtime.contracts import RetrievalRequest

RRF_CONSTANT = 60
logger = logging.getLogger(__name__)


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

        searches: list[tuple[str, Awaitable[list[RetrievedEvidence]]]] = []
        if request.plan.document:
            if request.knowledge_base_id is None:
                raise ValueError("document retrieval requires a knowledge base scope")
            searches.append(
                (
                    "document",
                    self._documents_factory().search(
                        RetrievalScope(
                            owner_id=request.owner_id,
                            knowledge_base_id=request.knowledge_base_id,
                        ),
                        request.question,
                        request.top_k,
                    ),
                )
            )
        if request.plan.memory:
            searches.append(
                (
                    "memory",
                    self._memories_factory().search(
                        owner_id=request.owner_id,
                        knowledge_base_id=request.knowledge_base_id,
                        query=request.question,
                        top_k=request.top_k,
                        temporal_scope=request.temporal_scope,
                        excluded_memory_types=PROFILE_MEMORY_TYPES if request.plan.profile else None,
                    ),
                )
            )
        if request.plan.profile:
            searches.append(
                (
                    "profile",
                    self._profile_factory().search(
                        owner_id=request.owner_id,
                        knowledge_base_id=request.knowledge_base_id,
                        query=request.question,
                        top_k=request.top_k,
                    ),
                )
            )
        if request.plan.relations:
            searches.append(
                (
                    "relation",
                    self._relations_factory().search(
                        owner_id=request.owner_id,
                        knowledge_base_id=request.knowledge_base_id,
                        query=request.question,
                        top_k=request.top_k,
                    ),
                )
            )

        results = await asyncio.gather(*(search for _, search in searches), return_exceptions=True)
        rankings: list[list[RetrievedEvidence]] = []
        first_error: Exception | None = None
        for (source, _), result in zip(searches, results, strict=True):
            if isinstance(result, BaseException):
                if isinstance(result, asyncio.CancelledError):
                    raise result
                if first_error is None and isinstance(result, Exception):
                    first_error = result
                safe_log(
                    logger,
                    logging.WARNING,
                    "answer_phase",
                    phase=f"retrieve_{source}",
                    status="failed",
                    error_code="AGENT_RETRIEVAL_SOURCE_FAILED",
                )
                continue
            rankings.append(result)

        if not rankings and first_error is not None:
            raise first_error
        return _reciprocal_rank_fusion(rankings, top_k=request.top_k)


def _reciprocal_rank_fusion(
    rankings: list[list[RetrievedEvidence]],
    *,
    top_k: int,
) -> list[RetrievedEvidence]:
    if top_k <= 0:
        return []
    items: dict[str, RetrievedEvidence] = {}
    scores: dict[str, float] = {}
    source_order: dict[str, int] = {}
    for ranking_index, ranking in enumerate(rankings):
        seen: set[str] = set()
        for rank, item in enumerate(ranking, start=1):
            if item.evidence_id in seen:
                continue
            seen.add(item.evidence_id)
            items.setdefault(item.evidence_id, item)
            source_order.setdefault(item.evidence_id, ranking_index)
            scores[item.evidence_id] = scores.get(item.evidence_id, 0.0) + 1.0 / (RRF_CONSTANT + rank)
    evidence_ids = sorted(
        scores,
        key=lambda evidence_id: (
            -scores[evidence_id],
            source_order[evidence_id],
            evidence_id,
        ),
    )[:top_k]
    return [
        items[evidence_id].model_copy(
            update={
                "score": scores[evidence_id],
                "metadata": {
                    **items[evidence_id].metadata,
                    "fusion": "rrf",
                },
            }
        )
        for evidence_id in evidence_ids
    ]
