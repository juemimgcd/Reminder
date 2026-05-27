import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from langchain_core.documents import Document as LCDocument

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.mneme.pipelines.memory_extract_pipeline import run_memory_extract_pipeline


async def main():
    chunk_docs = [
        LCDocument(
            page_content="The user is working on knowledge management and growth review.",
            metadata={
                "user_id": 1,
                "knowledge_base_id": "kb_demo_001",
                "knowledge_base_pk": 1,
                "document_id": "doc_demo_001",
                "document_pk": 1,
                "chunk_id": "doc_demo_001_chunk_0_x1",
                "page_no": 1,
            },
        )
    ]

    fake_entries = [
        {
            "id": "entry_001",
            "user_id": 1,
            "knowledge_base_id": "kb_demo_001",
            "knowledge_base_pk": 1,
            "document_id": "doc_demo_001",
            "document_pk": 1,
            "chunk_id": "doc_demo_001_chunk_0_x1",
            "page_no": 1,
            "entry_name": "鐭ヨ瘑绠＄悊",
            "entry_type": "theme",
            "summary": "闀挎湡鍏虫敞鐭ヨ瘑绠＄悊涓庢矇娣€",
                "evidence_text": "The user is working on knowledge management and growth review.",
            "importance_score": 0.8,
        },
        {
            "id": "entry_002",
            "user_id": 1,
            "knowledge_base_id": "kb_demo_001",
            "knowledge_base_pk": 1,
            "document_id": "doc_demo_001",
            "document_pk": 1,
            "chunk_id": "doc_demo_001_chunk_0_x1",
            "page_no": 1,
            "entry_name": "鐭ヨ瘑绠＄悊",
            "entry_type": "theme",
            "summary": "闀挎湡鍏虫敞鐭ヨ瘑绠＄悊涓庢矇娣€",
                "evidence_text": "The user is working on knowledge management and growth review.",
            "importance_score": 0.8,
        },
    ]

    with (
        patch(
            "pipelines.memory_extract_pipeline.extract_entries_from_chunks",
            new=AsyncMock(return_value=fake_entries),
        ),
        patch(
            "pipelines.memory_extract_pipeline.create_memory_entries",
            new=AsyncMock(return_value=[SimpleNamespace(id="entry_001")]),
        ),
    ):
        result = await run_memory_extract_pipeline(
            db=SimpleNamespace(),
            chunk_docs=chunk_docs,
            knowledge_base_id="kb_demo_001",
            document_id="doc_demo_001",
        )

    print("memory_pipeline_result")
    print(result.model_dump())


if __name__ == "__main__":
    asyncio.run(main())
