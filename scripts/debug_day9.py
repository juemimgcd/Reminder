import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from app.mneme.schemas.chat import ContextItem
from app.mneme.services.retrieval_fusion_service import fuse_and_rerank_context_items


def build_item(
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
        knowledge_base_id="debug_day9_kb",
        document_id=document_id,
        chunk_id=chunk_id,
        page_no=1,
        text=text,
        source_chunk_ids=[chunk_id],
        source_page_nos=[1],
        section_title=section_title,
        section_path=section_title,
        section_summary=section_title,
        matched_terms=matched_terms or [],
    )


def main():
    query_terms = ["FastAPI", "JWT", "Milvus"]
    vector_items = [
        build_item(
            recall_type="vector",
            score=0.92,
            document_id="doc_a",
            chunk_id="chunk_1",
            text="FastAPI backend project includes API design, authentication, and database integration.",
            section_title="鍚庣椤圭洰缁忛獙",
        ),
        build_item(
            recall_type="vector",
            score=0.88,
            document_id="doc_b",
            chunk_id="chunk_2",
            text="The knowledge base system integrates vector retrieval and long-term memory extraction.",
            section_title="RAG 绯荤粺",
        ),
    ]
    keyword_items = [
        build_item(
            recall_type="keyword",
            score=1.0,
            document_id="doc_a",
            chunk_id="chunk_1",
            text="FastAPI backend project includes API design, JWT auth, and database integration.",
            section_title="FastAPI JWT",
            matched_terms=["FastAPI", "JWT"],
        ),
        build_item(
            recall_type="keyword",
            score=1.0,
            document_id="doc_c",
            chunk_id="chunk_3",
            text="Milvus retrieval mainly solves vector recall and filtering.",
            section_title="Milvus retrieval",
            matched_terms=["Milvus"],
        ),
    ]
    memory_items = [
        build_item(
            recall_type="memory",
            score=0.7,
            document_id="doc_a",
            chunk_id="chunk_1",
            text="Previously worked on FastAPI, JWT auth, and Milvus retrieval integration.",
            section_title="椤圭洰璁板繂",
            matched_terms=["FastAPI", "JWT", "Milvus"],
        )
    ]

    ranked_items = fuse_and_rerank_context_items(
        vector_items=vector_items,
        lexical_items=keyword_items,
        memory_items=memory_items,
        query_terms=query_terms,
    )

    print("寮€濮嬫墽琛?Day 9 Fusion/Rerank 璋冭瘯鑴氭湰...", flush=True)
    for index, item in enumerate(ranked_items, start=1):
        print("=" * 60, flush=True)
        print(f"rank={index}", flush=True)
        print(f"chunk_id={item.chunk_id}", flush=True)
        print(f"recall_type={item.recall_type}", flush=True)
        print(f"vector_score={item.vector_score}", flush=True)
        print(f"keyword_score={item.keyword_score}", flush=True)
        print(f"memory_score={item.memory_score}", flush=True)
        print(f"fusion_score={item.fusion_score:.6f}", flush=True)
        print(f"rerank_score={item.rerank_score:.6f}", flush=True)
        print(f"exact_match_count={item.exact_match_count}", flush=True)
        print(f"recall_ranks={item.recall_ranks}", flush=True)
        print(f"rerank_reasons={item.rerank_reasons}", flush=True)


if __name__ == "__main__":
    main()
