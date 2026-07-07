import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.mneme.infra.circuit_breaker import _BREAKER_STATE
from app.mneme.infra.rate_limit import _WINDOW_COUNTERS
from app.mneme.domains.retrieval.context_service import (
    build_similarity_search_kwargs,
    deduplicate_retrieved_documents,
    merge_adjacent_scored_documents,
    trim_scored_documents_by_budget,
)
from app.mneme.tasks.index_tasks import index_document_task
from app.mneme.services.task_state_service import ALLOWED_TASK_TRANSITIONS
from app.mneme.pipelines.document_index_pipeline import run_document_index_pipeline
from app.mneme.pipelines.memory_extract_pipeline import run_memory_extract_pipeline


async def main():
    print("runtime_harness")
    print(f"task_entry={index_document_task.name}")
    print(f"state_machine_keys={list(ALLOWED_TASK_TRANSITIONS.keys())}")
    print(f"rate_limit_counter_type={type(_WINDOW_COUNTERS).__name__}")
    print(f"breaker_state_type={type(_BREAKER_STATE).__name__}")
    print()

    print("context_harness")
    print(build_similarity_search_kwargs(
        "什么是 RAG",
        top_k=4,
        user_id=1,
        knowledge_base_id="kb_demo_001",
    ))
    print(f"dedupe_fn={deduplicate_retrieved_documents.__name__}")
    print(f"merge_fn={merge_adjacent_scored_documents.__name__}")
    print(f"trim_fn={trim_scored_documents_by_budget.__name__}")
    print()

    print("module_boundary_harness")
    print(f"document_pipeline={run_document_index_pipeline.__name__}")
    print(f"memory_pipeline={run_memory_extract_pipeline.__name__}")
    print()

    print("dual_pipeline_foundation")
    print("document_domain=ready")
    print("memory_domain=pre-embedded")


if __name__ == "__main__":
    asyncio.run(main())
