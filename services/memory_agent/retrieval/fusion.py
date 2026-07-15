from collections.abc import Sequence

from services.memory_agent.retrieval.contracts import DocumentSearchHit, RetrievedEvidence

RRF_CONSTANT = 60


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[DocumentSearchHit]],
    *,
    top_k: int,
) -> list[RetrievedEvidence]:
    if top_k <= 0:
        return []

    hits_by_chunk_id: dict[str, DocumentSearchHit] = {}
    scores_by_chunk_id: dict[str, float] = {}
    for ranking in rankings:
        seen_chunk_ids: set[str] = set()
        for rank, hit in enumerate(ranking, start=1):
            if hit.chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(hit.chunk_id)
            hits_by_chunk_id.setdefault(hit.chunk_id, hit)
            scores_by_chunk_id[hit.chunk_id] = scores_by_chunk_id.get(hit.chunk_id, 0.0) + 1.0 / (
                RRF_CONSTANT + rank
            )

    ranked_chunk_ids = sorted(
        scores_by_chunk_id,
        key=lambda chunk_id: (-scores_by_chunk_id[chunk_id], chunk_id),
    )[:top_k]
    return [
        RetrievedEvidence(
            evidence_id=chunk_id,
            source_type="document",
            source_id=hits_by_chunk_id[chunk_id].document_id,
            content=hits_by_chunk_id[chunk_id].content,
            score=scores_by_chunk_id[chunk_id],
            metadata=hits_by_chunk_id[chunk_id].metadata,
        )
        for chunk_id in ranked_chunk_ids
    ]
