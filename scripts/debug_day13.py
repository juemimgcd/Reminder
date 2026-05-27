import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from app.mneme.services.memory_governance_service import build_memory_governance_view


def build_entry(
    *,
    entry_id: str,
    entry_name: str,
    entry_type: str,
    summary: str,
    evidence_text: str,
    document_id: str,
    created_at: datetime,
    importance_score: float = 0.5,
):
    return SimpleNamespace(
        id=entry_id,
        user_id=1,
        knowledge_base_id="debug_day13_kb",
        knowledge_base_pk=1,
        document_id=document_id,
        document_pk=1,
        chunk_id=f"{document_id}_chunk_1",
        entry_name=entry_name,
        entry_type=entry_type,
        summary=summary,
        evidence_text=evidence_text,
        importance_score=importance_score,
        created_at=created_at,
        updated_at=created_at,
    )


def main() -> None:
    base_time = datetime(2026, 5, 25, 9, 0, tzinfo=timezone.utc)
    entries = [
        build_entry(
            entry_id="entry_1",
            entry_name="Qwen embedding",
            entry_type="technology",
        summary="The project has completed Qwen embedding integration.",
        evidence_text="The embedding model has been switched to Qwen embedding.",
            document_id="doc_a",
            created_at=base_time,
            importance_score=0.8,
        ),
        build_entry(
            entry_id="entry_2",
            entry_name="Qwen embedding",
            entry_type="technology",
        summary="The project has completed Qwen embedding integration.",
        evidence_text="The embedding model has been switched to Qwen embedding.",
            document_id="doc_b",
            created_at=base_time + timedelta(minutes=5),
            importance_score=0.7,
        ),
        build_entry(
            entry_id="entry_3",
            entry_name="Qwen embedding",
            entry_type="technology",
        summary="The project has not completed Qwen embedding integration.",
        evidence_text="Qwen embedding migration is not completed yet.",
            document_id="doc_c",
            created_at=base_time + timedelta(days=1),
            importance_score=0.6,
        ),
        build_entry(
            entry_id="entry_4",
            entry_name="Redis broker",
            entry_type="architecture",
        summary="Redis remains the Celery broker for now.",
        evidence_text="Redis is still used; Celery may later move to RabbitMQ.",
            document_id="doc_d",
            created_at=base_time,
            importance_score=0.65,
        ),
    ]

    governance = build_memory_governance_view(
        knowledge_base_id="debug_day13_kb",
        entries=entries,
    )

    print("寮€濮嬫墽琛?Day 13 Memory Governance 璋冭瘯鑴氭湰...", flush=True)
    print(f"raw_entry_count={governance.raw_entry_count}", flush=True)
    print(f"canonical_memory_count={governance.canonical_memory_count}", flush=True)
    print(f"relation_count={governance.relation_count}", flush=True)
    print(f"relation_type_counts={governance.relation_type_counts}", flush=True)
    for item in governance.canonical_memories:
        print("=" * 60, flush=True)
        print(f"canonical_id={item.canonical_id}", flush=True)
        print(f"entry_name={item.entry_name}", flush=True)
        print(f"status={item.status}", flush=True)
        print(f"entry_ids={item.entry_ids}", flush=True)
    for relation in governance.relations:
        print("-" * 60, flush=True)
        print(f"relation_type={relation.relation_type}", flush=True)
        print(f"source={relation.source_entry_id}", flush=True)
        print(f"target={relation.target_entry_id}", flush=True)
        print(f"confidence={relation.confidence}", flush=True)
        print(f"reason={relation.reason}", flush=True)


if __name__ == "__main__":
    main()
