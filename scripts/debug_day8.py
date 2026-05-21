import asyncio
import sys
from pathlib import Path

from langchain_core.documents import Document as LCDocument

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from clients.elasticsearch_client import index_chunks_to_elasticsearch, is_elasticsearch_enabled, search_chunks_by_bm25
from conf.config import settings


async def main():
    print("开始执行 Day 8 Elasticsearch BM25 调试脚本...", flush=True)
    print(f"ELASTICSEARCH_ENABLED={settings.ELASTICSEARCH_ENABLED}", flush=True)
    print(f"ELASTICSEARCH_URL={settings.ELASTICSEARCH_URL}", flush=True)
    print(f"ELASTICSEARCH_INDEX_NAME={settings.ELASTICSEARCH_INDEX_NAME}", flush=True)

    sample_doc = LCDocument(
        page_content="FastAPI 项目中负责接口设计、JWT 鉴权、Milvus 检索和 Elasticsearch BM25 召回。",
        metadata={
            "chunk_id": "debug_day8_chunk_1",
            "document_id": "debug_day8_doc",
            "knowledge_base_id": "debug_day8_kb",
            "user_id": 1,
            "file_name": "debug_day8.md",
            "chunk_index": 0,
            "page_no": 1,
            "section_id": "debug_day8_doc_sec_0",
            "section_title": "Hybrid Search",
            "section_path": "Hybrid Search",
            "section_summary": "Hybrid Search: Elasticsearch BM25 召回验证",
            "section_chunk_index": 0,
        },
    )

    if not is_elasticsearch_enabled():
        result = await index_chunks_to_elasticsearch([sample_doc])
        hits = await search_chunks_by_bm25(
            query="Elasticsearch BM25",
            knowledge_base_id="debug_day8_kb",
            user_id=1,
            limit=3,
        )
        print("ES 未启用，本地验证 fallback 语义：", flush=True)
        print(f"index_result={result}", flush=True)
        print(f"search_result={hits}", flush=True)
        return

    index_result = await index_chunks_to_elasticsearch([sample_doc])
    hits = await search_chunks_by_bm25(
        query="Elasticsearch BM25",
        knowledge_base_id="debug_day8_kb",
        user_id=1,
        limit=3,
    )
    print(f"index_result={index_result}", flush=True)
    print(f"hit_count={len(hits or [])}", flush=True)
    for hit in hits or []:
        print(f"{hit.chunk_id} score={hit.score} section={hit.section_path}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
