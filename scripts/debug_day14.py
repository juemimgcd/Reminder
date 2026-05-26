import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from app.mneme.services.profile_tool_service import build_evidence_profile_from_entries


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
        knowledge_base_id="debug_day14_kb",
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
            entry_id="entry_fastapi_1",
            entry_name="FastAPI backend",
            entry_type="ability",
        summary="Continued implementation of FastAPI backend APIs and layered services.",
        evidence_text="Completed backend APIs for profile, memory, and graph.",
            document_id="doc_backend",
            created_at=base_time - timedelta(days=20),
            importance_score=0.8,
        ),
        build_entry(
            entry_id="entry_fastapi_2",
            entry_name="FastAPI backend",
            entry_type="ability",
        summary="Continued implementation of FastAPI backend APIs and layered services.",
        evidence_text="Continue adding memory governance and profile tools.",
            document_id="doc_backend_2",
            created_at=base_time - timedelta(days=3),
            importance_score=0.75,
        ),
        build_entry(
            entry_id="entry_goal_1",
            entry_name="Qwen embedding migration",
            entry_type="goal",
        summary="Next step is switching the embedding model to Qwen embedding.",
        evidence_text="The summary file includes the Qwen embedding replacement task.",
            document_id="doc_plan",
            created_at=base_time - timedelta(days=1),
            importance_score=0.7,
        ),
        build_entry(
            entry_id="entry_conflict_1",
            entry_name="Neo4j backend",
            entry_type="architecture",
        summary="Neo4j is enabled as the default graph backend.",
        evidence_text="GRAPH_BACKEND=neo4j and NEO4J_ENABLED=true.",
            document_id="doc_arch",
            created_at=base_time - timedelta(days=2),
            importance_score=0.65,
        ),
        build_entry(
            entry_id="entry_conflict_2",
            entry_name="Neo4j backend",
            entry_type="architecture",
        summary="Neo4j default enablement is not completed yet.",
        evidence_text="Neo4j default enablement has not been confirmed yet.",
            document_id="doc_old_arch",
            created_at=base_time - timedelta(days=1),
            importance_score=0.55,
        ),
    ]

    profile = build_evidence_profile_from_entries(
        knowledge_base_id="debug_day14_kb",
        entries=entries,
        recent_days=7,
    )

    print("寮€濮嬫墽琛?Day 14 Evidence Profile 璋冭瘯鑴氭湰...", flush=True)
    print(f"entry_count={profile.entry_count}", flush=True)
    print(f"canonical_memory_count={profile.canonical_memory_count}", flush=True)
    print(f"stable_trait_count={len(profile.stable_traits)}", flush=True)
    print(f"recent_focus_count={len(profile.recent_focus)}", flush=True)
    print(f"goal_count={len(profile.goals)}", flush=True)
    print(f"risk_count={len(profile.risks)}", flush=True)
    print(f"evidence_count={len(profile.evidence)}", flush=True)
    print(f"tool_call_count={len(profile.tool_calls)}", flush=True)
    print(f"uncertainty={profile.uncertainty}", flush=True)
    for call in profile.tool_calls:
        print("=" * 60, flush=True)
        print(f"tool_name={call.tool_name}", flush=True)
        print(f"output_count={call.output_count}", flush=True)
        print(f"evidence_entry_ids={call.evidence_entry_ids}", flush=True)
    for risk in profile.risks:
        print("-" * 60, flush=True)
        print(f"risk_name={risk.risk_name}", flush=True)
        print(f"relation_type={risk.relation_type}", flush=True)
        print(f"evidence_entry_ids={risk.evidence_entry_ids}", flush=True)


if __name__ == "__main__":
    main()
