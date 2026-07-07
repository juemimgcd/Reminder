import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from app.mneme.schemas.chat import ContextItem
from app.mneme.domains.retrieval.query_router import route_query
from app.mneme.domains.retrieval.debug import build_answer_debug, build_retrieval_debug_packet
from app.mneme.domains.retrieval.fusion import fuse_and_rerank_context_items


def build_item(
    *,
    recall_type: str,
    score: float,
    document_id: str,
    chunk_id: str,
    text: str,
    matched_terms: list[str] | None = None,
) -> ContextItem:
    return ContextItem(
        recall_type=recall_type,
        score=score,
        knowledge_base_id="debug_day10_kb",
        document_id=document_id,
        chunk_id=chunk_id,
        page_no=1,
        text=text,
        source_chunk_ids=[chunk_id],
        source_page_nos=[1],
        section_title="Retrieval Debug",
        section_path="RAG > Retrieval Debug",
        section_summary="璁板綍 router銆乺ecall銆乫usion銆乺erank 鍜?citation",
        matched_terms=matched_terms or [],
    )


def main():
    question = "FastAPI JWT Milvus 鐨勬绱㈣皟璇曟€庝箞鍋氾紵"
    query_terms = ["FastAPI", "JWT", "Milvus"]
    route = route_query(question)

    vector_items = [
        build_item(
            recall_type="vector",
            score=0.91,
            document_id="doc_debug",
            chunk_id="chunk_debug_1",
            text="FastAPI project needs retrieval tracing with vector recall, rerank, and evidence citations.",
            matched_terms=["FastAPI"],
        )
    ]
    lexical_items = [
        build_item(
            recall_type="keyword",
            score=1.0,
            document_id="doc_debug",
            chunk_id="chunk_debug_1",
            text="FastAPI JWT Milvus retrieval debug needs keyword recall, fusion, and rerank traces.",
            matched_terms=["FastAPI", "JWT", "Milvus"],
        )
    ]
    memory_items = [
        build_item(
            recall_type="memory",
            score=0.75,
            document_id="doc_debug",
            chunk_id="chunk_debug_1",
            text="Implemented FastAPI, JWT auth, Milvus retrieval, and retrieval debug.",
            matched_terms=["FastAPI", "JWT", "Milvus"],
        )
    ]

    fused_items = fuse_and_rerank_context_items(
        vector_items=vector_items,
        lexical_items=lexical_items,
        memory_items=memory_items,
        query_terms=query_terms,
    )
    final_items = fused_items[:1]
    debug = build_retrieval_debug_packet(
        query_terms=query_terms,
        lexical_backend="postgres_keyword",
        counts={
            "raw_count": 1,
            "dedup_count": 1,
            "vector_count": len(vector_items),
            "lexical_count": len(lexical_items),
            "memory_count": len(memory_items),
            "candidate_count": len(vector_items) + len(lexical_items) + len(memory_items),
            "fusion_count": len(fused_items),
            "rerank_count": len(fused_items),
            "final_count": len(final_items),
        },
        vector_items=vector_items,
        lexical_items=lexical_items,
        memory_items=memory_items,
        fused_items=fused_items,
        final_items=final_items,
    )
    debug["route"] = route.model_dump()
    debug["answer_debug"] = build_answer_debug(
            answer="Use router, recall, fusion, rerank, and citation traces to locate issues.",
        sources=[
            {
                "source_id": "S1",
                "document_id": "doc_debug",
                "chunk_id": "chunk_debug_1",
            }
        ],
        citations=[
            {
                "source_id": "S1",
                "document_id": "doc_debug",
                "chunk_id": "chunk_debug_1",
            }
        ],
        confidence="medium",
        uncertainty=None,
    )

    print("寮€濮嬫墽琛?Day 10 Retrieval Debug 璋冭瘯鑴氭湰...", flush=True)
    print(f"query_type={debug['route']['query_type']}", flush=True)
    print(f"lexical_backend={debug['lexical_backend']}", flush=True)
    print(f"counts={debug['counts']}", flush=True)
    print(f"vector_candidate_count={len(debug['vector_candidates'])}", flush=True)
    print(f"lexical_candidate_count={len(debug['lexical_candidates'])}", flush=True)
    print(f"memory_candidate_count={len(debug['memory_candidates'])}", flush=True)
    print(f"fused_top_recall_type={debug['fused_candidates'][0]['recall_type']}", flush=True)
    print(f"final_context_count={len(debug['final_context'])}", flush=True)
    print(f"answer_debug={debug['answer_debug']}", flush=True)


if __name__ == "__main__":
    main()
