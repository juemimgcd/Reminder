import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from schemas.chat import ContextItem
from services.query_router_service import route_query
from services.retrieval_debug_service import build_answer_debug, build_retrieval_debug_packet
from services.retrieval_fusion_service import fuse_and_rerank_context_items


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
        section_summary="记录 router、recall、fusion、rerank 和 citation",
        matched_terms=matched_terms or [],
    )


def main():
    question = "FastAPI JWT Milvus 的检索调试怎么做？"
    query_terms = ["FastAPI", "JWT", "Milvus"]
    route = route_query(question)

    vector_items = [
        build_item(
            recall_type="vector",
            score=0.91,
            document_id="doc_debug",
            chunk_id="chunk_debug_1",
            text="FastAPI 项目里需要记录检索链路，包含向量召回、重排和证据引用。",
            matched_terms=["FastAPI"],
        )
    ]
    lexical_items = [
        build_item(
            recall_type="keyword",
            score=1.0,
            document_id="doc_debug",
            chunk_id="chunk_debug_1",
            text="FastAPI JWT Milvus 的 Retrieval Debug 需要记录 keyword recall、fusion 和 rerank。",
            matched_terms=["FastAPI", "JWT", "Milvus"],
        )
    ]
    memory_items = [
        build_item(
            recall_type="memory",
            score=0.75,
            document_id="doc_debug",
            chunk_id="chunk_debug_1",
            text="曾经实现过 FastAPI、JWT 鉴权、Milvus 检索和 Retrieval Debug。",
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
        answer="可以通过记录 router、recall、fusion、rerank 和 citation 来定位问题。",
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

    print("开始执行 Day 10 Retrieval Debug 调试脚本...", flush=True)
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
