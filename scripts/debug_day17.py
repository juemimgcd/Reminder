import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from app.mneme.domains.tasks.outbox import (
    BACKEND_MILVUS,
    BACKEND_NEO4J,
    EVENT_DOCUMENT_GRAPH_SYNC,
    EVENT_DOCUMENT_VECTOR_REINDEX,
    OUTBOX_DEAD_LETTER,
    OUTBOX_FAILED,
    OUTBOX_PENDING,
    OUTBOX_RUNNING,
    OUTBOX_SUCCEEDED,
    build_chunk_document,
    build_outbox_idempotency_key,
    calculate_next_attempt_at,
    should_dead_letter,
)


def main() -> None:
    print("Start Day 17 Outbox debug script...", flush=True)
    print(f"statuses={[OUTBOX_PENDING, OUTBOX_RUNNING, OUTBOX_SUCCEEDED, OUTBOX_FAILED, OUTBOX_DEAD_LETTER]}", flush=True)
    print(f"event_types={[EVENT_DOCUMENT_VECTOR_REINDEX, EVENT_DOCUMENT_GRAPH_SYNC]}", flush=True)
    print(f"backends={[BACKEND_MILVUS, BACKEND_NEO4J]}", flush=True)

    key = build_outbox_idempotency_key(
        event_type=EVENT_DOCUMENT_VECTOR_REINDEX,
        aggregate_type="document",
        aggregate_id="doc_day17",
        operation_id="index_run_001",
    )
    print(f"idempotency_key={key}", flush=True)

    next_attempt = calculate_next_attempt_at(attempt_count=2)
    print(f"next_attempt_is_future={next_attempt > datetime.now(timezone.utc)}", flush=True)
    print(f"dead_letter_before_limit={should_dead_letter(attempt_count=2, max_attempts=5)}", flush=True)
    print(f"dead_letter_at_limit={should_dead_letter(attempt_count=5, max_attempts=5)}", flush=True)

    document = SimpleNamespace(
        id="doc_day17",
        pk=17,
        user_id=1,
        knowledge_base_id="kb_day17",
        knowledge_base_pk=1,
        file_name="day17.md",
        file_type="md",
        file_path="storage/raw/day17.md",
    )
    chunk = SimpleNamespace(
        id="chunk_day17_1",
        content="Outbox records external projection work for Milvus and Neo4j.",
        chunk_index=0,
        page_no=1,
        start_offset=0,
        end_offset=64,
        section_id="sec_1",
        section_title="Outbox",
        section_level=1,
        section_path="Outbox",
        section_summary="Outbox consistency boundary",
        section_chunk_index=0,
    )
    chunk_doc = build_chunk_document(document, chunk)
    print(f"chunk_doc_id={chunk_doc.metadata['chunk_id']}", flush=True)
    print(f"chunk_doc_backend_payload_document_id={chunk_doc.metadata['document_id']}", flush=True)
    print(f"chunk_doc_has_section={bool(chunk_doc.metadata['section_id'])}", flush=True)


if __name__ == "__main__":
    main()
