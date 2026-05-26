import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from app.mneme.services.graph_rag_service import build_graph_rag_decision, compare_graph_retrieval


def build_document(*, document_id: str, file_name: str, created_at: datetime):
    return SimpleNamespace(
        id=document_id,
        knowledge_base_id="debug_day15_kb",
        file_name=file_name,
        file_type="md",
        file_size=1024,
        status="processed",
        created_at=created_at,
        updated_at=created_at,
    )


def build_entry(
    *,
    entry_id: str,
    entry_name: str,
    entry_type: str,
    summary: str,
    evidence_text: str,
    document_id: str,
    chunk_id: str,
    created_at: datetime,
    importance_score: float = 0.5,
):
    return SimpleNamespace(
        id=entry_id,
        user_id=1,
        knowledge_base_id="debug_day15_kb",
        knowledge_base_pk=1,
        document_id=document_id,
        document_pk=1,
        chunk_id=chunk_id,
        entry_name=entry_name,
        entry_type=entry_type,
        summary=summary,
        evidence_text=evidence_text,
        importance_score=importance_score,
        created_at=created_at,
        updated_at=created_at,
    )


def main() -> None:
    base_time = datetime(2026, 5, 25, 9, 0, tzinfo=timezone.utc)
    documents = [
        build_document(
            document_id="doc_arch",
            file_name="architecture_notes.md",
            created_at=base_time - timedelta(days=4),
        ),
        build_document(
            document_id="doc_embedding",
            file_name="embedding_plan.md",
            created_at=base_time - timedelta(days=2),
        ),
        build_document(
            document_id="doc_ops",
            file_name="ops_notes.md",
            created_at=base_time - timedelta(days=1),
        ),
    ]
    entries = [
        build_entry(
            entry_id="entry_neo4j_seed",
            entry_name="Neo4j backend",
            entry_type="architecture",
            summary="Neo4j is the graph backend used for GraphRAG document and memory relations.",
            evidence_text="The graph router can read Neo4j projection first and fall back to PostgreSQL.",
            document_id="doc_arch",
            chunk_id="doc_arch_chunk_1",
            created_at=base_time - timedelta(days=4),
            importance_score=0.85,
        ),
        build_entry(
            entry_id="entry_shared_arch",
            entry_name="GraphRAG expansion",
            entry_type="retrieval",
            summary="GraphRAG expansion connects seed memories to related documents through shared memory entries.",
            evidence_text="Related document edges are generated from shared MemoryEntry signatures.",
            document_id="doc_arch",
            chunk_id="doc_arch_chunk_2",
            created_at=base_time - timedelta(days=3),
            importance_score=0.75,
        ),
        build_entry(
            entry_id="entry_shared_embedding",
            entry_name="GraphRAG expansion",
            entry_type="retrieval",
            summary="GraphRAG expansion should be evaluated before it is added to the answer context.",
            evidence_text="The embedding migration plan mentions Qwen embedding and graph-expanded evidence.",
            document_id="doc_embedding",
            chunk_id="doc_embedding_chunk_1",
            created_at=base_time - timedelta(days=2),
            importance_score=0.8,
        ),
        build_entry(
            entry_id="entry_qwen_embedding",
            entry_name="Qwen embedding model",
            entry_type="model",
            summary="The embedding model migration target is Qwen embedding.",
            evidence_text="The company target summary includes replacing the embedding model with Qwen embedding.",
            document_id="doc_embedding",
            chunk_id="doc_embedding_chunk_2",
            created_at=base_time - timedelta(days=2),
            importance_score=0.7,
        ),
        build_entry(
            entry_id="entry_redis_keep",
            entry_name="Redis",
            entry_type="infrastructure",
            summary="Redis remains in the runtime stack while Celery may later move to RabbitMQ as broker.",
            evidence_text="The project keeps Redis and does not remove it during database stack cleanup.",
            document_id="doc_ops",
            chunk_id="doc_ops_chunk_1",
            created_at=base_time - timedelta(days=1),
            importance_score=0.65,
        ),
    ]

    decision = build_graph_rag_decision(
        knowledge_base_id="debug_day15_kb",
        query="Neo4j backend relationship",
        documents=documents,
        entries=entries,
        top_k=5,
        max_expansions=6,
    )
    comparison = compare_graph_retrieval(
        decision=decision,
        expected_source_chunk_ids=["doc_embedding_chunk_1"],
        k=5,
    )

    print("Start Day 15 GraphRAG debug script...", flush=True)
    print(f"graph_useful={decision.graph_useful}", flush=True)
    print(f"reason={decision.reason}", flush=True)
    print(f"query_terms={decision.query_terms}", flush=True)
    print(f"seed_count={decision.seed_count}", flush=True)
    print(f"expansion_count={decision.expansion_count}", flush=True)
    print(f"context_count={decision.context_count}", flush=True)
    print(f"baseline_chunk_ids={comparison.baseline_chunk_ids}", flush=True)
    print(f"graph_chunk_ids={comparison.graph_chunk_ids}", flush=True)
    print(f"baseline_recall_at_k={comparison.baseline.recall_at_k:.4f}", flush=True)
    print(f"graph_recall_at_k={comparison.graph.recall_at_k:.4f}", flush=True)
    print(f"recall_delta={comparison.delta['recall_at_k']:.4f}", flush=True)
    for expansion in decision.expansions:
        print("=" * 60, flush=True)
        print(f"edge_id={expansion.edge_id}", flush=True)
        print(f"source_document_id={expansion.source_document_id}", flush=True)
        print(f"target_document_id={expansion.target_document_id}", flush=True)
        print(f"relationship_score={expansion.relationship_score:.4f}", flush=True)
        print(f"evidence_entry_ids={expansion.evidence_entry_ids}", flush=True)


if __name__ == "__main__":
    main()
