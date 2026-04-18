import sys
from pathlib import Path

from langchain_core.documents import Document as LCDocument

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from services.context_service import (
    build_source_item,
    deduplicate_retrieved_documents,
    format_context_docs,
    merge_adjacent_scored_documents,
    trim_scored_documents_by_budget,
)


def build_doc(
        *,
        text: str,
        document_id: str,
        chunk_id: str,
        chunk_index: int,
        page_no: int,
        knowledge_base_id: str = "kb_demo_001",
) -> LCDocument:
    return LCDocument(
        page_content=text,
        metadata={
            "knowledge_base_id": knowledge_base_id,
            "document_id": document_id,
            "chunk_id": chunk_id,
            "chunk_index": chunk_index,
            "page_no": page_no,
        },
    )


def main():
    raw_items = [
        (
            build_doc(
                text="FastAPI 项目中负责接口设计、JWT 鉴权和数据库联调。",
                document_id="doc_a",
                chunk_id="doc_a_chunk_2",
                chunk_index=2,
                page_no=1,
            ),
            0.08,
        ),
        (
            build_doc(
                text="FastAPI 项目中负责接口设计、JWT 鉴权和数据库联调。",
                document_id="doc_a",
                chunk_id="doc_a_chunk_2_dup",
                chunk_index=2,
                page_no=1,
            ),
            0.09,
        ),
        (
            build_doc(
                text="还实现了 Docker 部署、日志整理和接口文档输出。",
                document_id="doc_a",
                chunk_id="doc_a_chunk_3",
                chunk_index=3,
                page_no=1,
            ),
            0.12,
        ),
        (
            build_doc(
                text="也做过 Milvus 检索接入和知识库问答实验。",
                document_id="doc_b",
                chunk_id="doc_b_chunk_1",
                chunk_index=1,
                page_no=2,
            ),
            0.15,
        ),
    ]

    deduped_items = deduplicate_retrieved_documents(raw_items)
    merged_items = merge_adjacent_scored_documents(deduped_items, max_merged_length=200)
    final_items = trim_scored_documents_by_budget(merged_items, max_chars=80)
    final_docs = [doc for doc, _ in final_items]

    print(f"raw_count={len(raw_items)}")
    print(f"dedup_count={len(deduped_items)}")
    print(f"merged_count={len(merged_items)}")
    print(f"final_count={len(final_items)}")
    print("=" * 60)
    print(format_context_docs(final_docs))
    print("=" * 60)
    for doc in final_docs:
        print(build_source_item(doc))


if __name__ == "__main__":
    main()
