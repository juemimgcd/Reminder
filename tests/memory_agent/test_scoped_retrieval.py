import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from services.memory_agent.retrieval.contracts import DocumentSearchHit, RetrievalScope
from services.memory_agent.retrieval.documents import DocumentRetriever
from services.memory_agent.retrieval.fusion import reciprocal_rank_fusion
from services.memory_agent.retrieval.memories import MemoryRetriever


def test_reciprocal_rank_fusion_is_deterministic_and_exact_top_k():
    left = [DocumentSearchHit("c1", "d1", "one", {}), DocumentSearchHit("c2", "d2", "two", {})]
    right = [DocumentSearchHit("c2", "d2", "two", {}), DocumentSearchHit("c3", "d3", "three", {})]

    first = reciprocal_rank_fusion((left, right), top_k=2)
    second = reciprocal_rank_fusion((right, left), top_k=2)

    assert len(first) == 2
    assert [item.evidence_id for item in first] == [item.evidence_id for item in second]
    assert first[0].evidence_id == "c2"


class _ReadSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def execute(self, statement):
        return SimpleNamespace(
            mappings=lambda: SimpleNamespace(
                all=lambda: [
                    {
                        "memory_id": "m1",
                        "memory_type": "preference",
                        "confidence": 0.9,
                        "revision_id": "r1",
                        "subject": "format",
                        "predicate": "prefers",
                        "value": "concise",
                        "valid_from": None,
                        "valid_to": None,
                    }
                ]
            )
        )


def test_memory_retriever_maps_current_rows_to_scoped_evidence():
    with patch(
        "services.memory_agent.retrieval.memories.open_read_session",
        return_value=_ReadSession(),
    ):
        result = asyncio.run(
            MemoryRetriever().search(
                owner_id=7,
                knowledge_base_id="kb-1",
                query="format",
                top_k=1,
            )
        )

    assert result[0].source_type == "memory"
    assert result[0].source_id == "m1"
    assert result[0].metadata["memory_type"] == "preference"


def test_document_retriever_passes_scope_and_top_k_to_both_recall_ports():
    vector = AsyncMock(return_value=[])
    keyword = AsyncMock(return_value=[])
    with (
        patch("services.memory_agent.retrieval.documents.search_vector", vector),
        patch("services.memory_agent.retrieval.documents.search_keyword", keyword),
        patch("services.memory_agent.retrieval.documents.open_read_session", return_value=_ReadSession()),
    ):
        asyncio.run(DocumentRetriever().search(RetrievalScope(owner_id=7, knowledge_base_id="kb-1"), "query", 3))

    vector.assert_awaited_once()
    keyword.assert_awaited_once()
    assert vector.await_args.kwargs["scope"].owner_id == 7
    assert vector.await_args.kwargs["limit"] == 3
