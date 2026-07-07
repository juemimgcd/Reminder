import asyncio
import unittest
from unittest.mock import patch

from app.mneme.schemas.chat import ContextItem
from app.mneme.domains.retrieval.fusion import (
    fuse_and_rerank_context_items,
    fuse_context_items_by_rrf,
    rerank_context_items,
)


def context_item(
    *,
    recall_type: str,
    score: float,
    document_id: str,
    chunk_id: str,
    text: str,
    section_title: str | None = None,
    matched_terms: list[str] | None = None,
) -> ContextItem:
    return ContextItem(
        recall_type=recall_type,
        score=score,
        knowledge_base_id="kb-1",
        document_id=document_id,
        chunk_id=chunk_id,
        text=text,
        source_chunk_ids=[chunk_id],
        section_title=section_title,
        matched_terms=matched_terms or [],
    )


class RetrievalFusionServiceTest(unittest.TestCase):
    def test_rrf_fusion_merges_same_chunk_across_recall_sources(self):
        fused = fuse_context_items_by_rrf(
            recall_groups={
                "vector": [
                    context_item(
                        recall_type="vector",
                        score=0.9,
                        document_id="doc-1",
                        chunk_id="chunk-1",
                        text="vector evidence",
                    )
                ],
                "keyword": [
                    context_item(
                        recall_type="keyword",
                        score=0.8,
                        document_id="doc-1",
                        chunk_id="chunk-1",
                        text="keyword evidence",
                        matched_terms=["memory"],
                    )
                ],
            }
        )

        self.assertEqual(len(fused), 1)
        self.assertEqual(fused[0].recall_type, "vector+keyword")
        self.assertEqual(fused[0].vector_score, 0.9)
        self.assertEqual(fused[0].keyword_score, 0.8)
        self.assertEqual(fused[0].recall_ranks, {"vector": 1, "keyword": 1})
        self.assertGreater(fused[0].fusion_score, 0)
        self.assertEqual(fused[0].matched_terms, ["memory"])

    def test_heuristic_rerank_rewards_exact_section_and_multi_source_matches(self):
        items = [
            context_item(
                recall_type="vector",
                score=0.05,
                document_id="doc-1",
                chunk_id="chunk-1",
                text="generic text",
            ),
            context_item(
                recall_type="vector+keyword",
                score=0.04,
                document_id="doc-2",
                chunk_id="chunk-2",
                text="this chunk explains graph memory retrieval",
                section_title="Graph Retrieval",
            ),
        ]
        items[0].fusion_score = 0.05
        items[1].fusion_score = 0.04

        reranked = rerank_context_items(items, query_terms=["graph", "retrieval"])

        self.assertEqual(reranked[0].chunk_id, "chunk-2")
        self.assertIn("exact_text_match", reranked[0].rerank_reasons)
        self.assertIn("section_match", reranked[0].rerank_reasons)
        self.assertIn("multi_source", reranked[0].rerank_reasons)

    def test_fuse_and_rerank_skips_model_reranker_when_disabled(self):
        with patch("app.mneme.domains.retrieval.fusion.settings.RERANKER_ENABLED", False):
            result = asyncio.run(
                fuse_and_rerank_context_items(
                    query="graph retrieval",
                    vector_items=[
                        context_item(
                            recall_type="vector",
                            score=0.9,
                            document_id="doc-1",
                            chunk_id="chunk-1",
                            text="graph retrieval evidence",
                        )
                    ],
                    lexical_items=[],
                    memory_items=[],
                    query_terms=["graph", "retrieval"],
                )
            )

        self.assertEqual(result[0].chunk_id, "chunk-1")
        self.assertNotIn("bge_reranker", result[0].rerank_reasons)


if __name__ == "__main__":
    unittest.main()
