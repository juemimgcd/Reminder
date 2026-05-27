import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from langchain_core.documents import Document as LCDocument

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.mneme.pipelines.document_index_pipeline import run_document_index_pipeline


async def main():
    stage_events: list[str] = []

    async def report_stage(stage: str) -> None:
        stage_events.append(stage)

    fake_document = SimpleNamespace(
        id="doc_demo_001",
        pk=1,
        user_id=1,
        knowledge_base_id="kb_demo_001",
        knowledge_base_pk=1,
        file_name="demo.txt",
        file_path="storage/raw/demo.txt",
        file_type="txt",
    )

    fake_loaded_docs = [
            LCDocument(page_content="First source paragraph", metadata={}),
    ]
    fake_chunk_docs = [
        LCDocument(
            page_content="绗竴娈?chunk",
            metadata={
                "chunk_id": "doc_demo_001_chunk_0_x1",
                "chunk_index": 0,
                "page_no": 1,
                "start_offset": 0,
            },
        )
    ]

    with (
        patch(
            "pipelines.document_index_pipeline.update_document_status_with_projection",
            new=AsyncMock(side_effect=[fake_document, fake_document]),
        ),
        patch(
            "pipelines.document_index_pipeline.load_langchain_documents",
            new=AsyncMock(return_value=fake_loaded_docs),
        ),
        patch(
            "pipelines.document_index_pipeline.split_documents",
            new=AsyncMock(return_value=fake_chunk_docs),
        ),
        patch(
            "pipelines.document_index_pipeline.persist_chunks_for_document",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "pipelines.document_index_pipeline.rebuild_memory_entries_for_document",
            new=AsyncMock(
                return_value={
                    "chunk_count": 1,
                    "deleted_entry_count": 0,
                    "entry_count": 0,
                }
            ),
        ),
        patch(
            "pipelines.document_index_pipeline.add_documents_to_vector_store_in_batches",
            new=AsyncMock(
                return_value={
                    "batch_count": 1,
                    "batch_size": 64,
                    "total_count": 1,
                }
            ),
        ),
    ):
        result = await run_document_index_pipeline(
            document=fake_document,
            on_stage_change=report_stage,
        )

    print("stage_events")
    print(stage_events)
    print()

    print("pipeline_result")
    print(result.model_dump())


if __name__ == "__main__":
    asyncio.run(main())
