import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.mneme.conf.config import settings
from app.mneme.services.context_service import build_query_context
from app.mneme.pipelines.document_index_pipeline import run_document_index_pipeline
from app.mneme.pipelines.memory_extract_pipeline import run_memory_extract_pipeline


async def main():
    print("verification_gate_examples")
    print("document_index_gate=chunk_count > 0, indexed_vector_count > 0")
    print("context_gate=raw_count >= dedup_count >= final_count")
    print("memory_gate=raw_entry_count >= dedup_entry_count >= persisted_entry_count")
    print()

    print("policy_examples")
    print(f"index_vector_batch_size={settings.INDEX_VECTOR_BATCH_SIZE}")
    print(f"retry_max_attempts={settings.EXTERNAL_RETRY_MAX_ATTEMPTS}")
    print(f"breaker_failure_threshold={settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD}")
    print("chunk_policy_source=clients/text_splitter_client.py")
    print("context_budget_source=services/context_service.py")
    print()

    print("observability_examples")
    print(f"document_pipeline_fn={run_document_index_pipeline.__name__}")
    print(f"memory_pipeline_fn={run_memory_extract_pipeline.__name__}")
    print(f"context_builder_fn={build_query_context.__name__}")


if __name__ == "__main__":
    asyncio.run(main())