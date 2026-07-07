import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from app.mneme.domains.analysis.service import build_analytics_report_from_snapshots


def item(**kwargs):
    return SimpleNamespace(**kwargs)


def main() -> None:
    print("Start Day 18 Analytics debug script...", flush=True)
    documents = [
        item(id="doc_a", status="indexed", file_size=1200),
        item(id="doc_b", status="failed", file_size=800),
        item(id="doc_c", status="queued", file_size=600),
    ]
    chunks = [
        item(id="chunk_a1", document_id="doc_a", section_id="intro"),
        item(id="chunk_a2", document_id="doc_a", section_id="arch"),
        item(id="chunk_b1", document_id="doc_b", section_id="arch"),
        item(id="chunk_c1", document_id="doc_c", section_id=None),
    ]
    memory_entries = [
        item(id="mem_1", entry_type="architecture"),
        item(id="mem_2", entry_type="goal"),
        item(id="mem_3", entry_type="architecture"),
    ]
    task_records = [
        item(id="task_1", status="succeeded"),
        item(id="task_2", status="running"),
        item(id="task_3", status="failed"),
    ]
    outbox_events = [
        item(id="outbox_1", target_backend="milvus", status="succeeded"),
        item(id="outbox_2", target_backend="neo4j", status="failed"),
        item(id="outbox_3", target_backend="neo4j", status="dead_letter"),
    ]

    report = build_analytics_report_from_snapshots(
        knowledge_base_id="debug_day18_kb",
        documents=documents,
        chunks=chunks,
        memory_entries=memory_entries,
        task_records=task_records,
        outbox_events=outbox_events,
        generated_at=datetime(2026, 5, 26, 15, 0, tzinfo=timezone.utc),
    )

    print(f"document_count={report.documents.document_count}", flush=True)
    print(f"total_file_size={report.documents.total_file_size}", flush=True)
    print(f"chunk_count={report.chunks.chunk_count}", flush=True)
    print(f"section_count={report.chunks.section_count}", flush=True)
    print(f"avg_chunks_per_document={report.chunks.avg_chunks_per_document:.2f}", flush=True)
    print(f"memory_entry_count={report.memory.memory_entry_count}", flush=True)
    print(f"task_count={report.tasks.task_count}", flush=True)
    print(f"active_task_count={report.tasks.active_task_count}", flush=True)
    print(f"failed_task_count={report.tasks.failed_task_count}", flush=True)
    print(f"outbox_event_count={report.outbox.event_count}", flush=True)
    print(f"outbox_failed_event_count={report.outbox.failed_event_count}", flush=True)
    print(f"outbox_dead_letter_count={report.outbox.dead_letter_count}", flush=True)
    print(f"markdown_has_dead_letter={'outbox_dead_letter: 1' in report.markdown}", flush=True)


if __name__ == "__main__":
    main()
