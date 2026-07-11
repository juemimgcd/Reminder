import unittest
from datetime import datetime
from types import SimpleNamespace

from app.mneme.domains.graph.rag import (
    build_graph_rag_decision,
    should_use_graph_expansion,
)


def document(document_id: str, file_name: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=document_id,
        file_name=file_name,
        knowledge_base_id="kb-1",
    )


def memory_entry(
    entry_id: str,
    *,
    document_id: str,
    chunk_id: str,
    entry_name: str,
    entry_type: str = "concept",
    summary: str = "architecture memory",
    evidence_text: str = "architecture evidence",
    importance_score: float = 0.8,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=entry_id,
        entry_name=entry_name,
        entry_type=entry_type,
        summary=summary,
        evidence_text=evidence_text,
        document_id=document_id,
        chunk_id=chunk_id,
        importance_score=importance_score,
        created_at=datetime(2026, 1, 1),
    )


class GraphRagServiceTest(unittest.TestCase):
    def test_decision_uses_shared_memory_edges_for_related_documents(self):
        decision = build_graph_rag_decision(
            knowledge_base_id="kb-1",
            query="architecture relationship",
            documents=[
                document("doc-1", "first.md"),
                document("doc-2", "second.md"),
            ],
            entries=[
                memory_entry("entry-1", document_id="doc-1", chunk_id="chunk-1", entry_name="Architecture"),
                memory_entry("entry-2", document_id="doc-2", chunk_id="chunk-2", entry_name="Architecture"),
            ],
            top_k=6,
            max_expansions=4,
        )

        self.assertTrue(decision.graph_useful)
        self.assertEqual(decision.seed_count, 2)
        self.assertEqual(decision.expansion_count, 1)
        self.assertEqual(decision.expansions[0].source_document_id, "doc-1")
        self.assertEqual(decision.expansions[0].target_document_id, "doc-2")
        self.assertGreater(decision.context_count, 0)

    def test_graph_expansion_is_not_useful_without_seed_memories(self):
        graph_useful, reason = should_use_graph_expansion(
            query="relationship between documents",
            seeds=[],
            expansions=[],
        )

        self.assertFalse(graph_useful)
        self.assertIn("No seed memory", reason)


if __name__ == "__main__":
    unittest.main()
