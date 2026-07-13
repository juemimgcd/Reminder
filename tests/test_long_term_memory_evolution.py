import asyncio
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.mneme.domains.memory.identity import (
    build_memory_entry_id,
    build_memory_source_fingerprint,
    prepare_memory_entry_payload,
)
from app.mneme.domains.memory.projection import rebuild_memory_governance_projection
from app.mneme.domains.memory.service import reconcile_memory_entries_for_document
from app.mneme.models.memory import CanonicalMemory, MemoryEntry, MemoryRelation, canonical_memory_evidence

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "alembic/versions/20260713_01_add_long_term_memory_evolution.py"


def memory_payload(**overrides):
    payload = {
        "id": "temporary-id",
        "user_id": 7,
        "knowledge_base_id": "kb_1",
        "knowledge_base_pk": 11,
        "document_id": "doc_1",
        "document_pk": 13,
        "chunk_id": "chunk_1",
        "entry_name": "Agent architecture",
        "entry_type": "topic",
        "summary": "The user is studying agent architecture.",
        "evidence_text": "I am studying agent architecture.",
        "importance_score": 0.8,
        "extraction_version": "v1",
        "confidence": 0.7,
    }
    payload.update(overrides)
    return payload


def document():
    return SimpleNamespace(
        id="doc_1",
        pk=13,
        user_id=7,
        knowledge_base_id="kb_1",
        knowledge_base_pk=11,
    )


class FakeDatabase:
    def __init__(self):
        self.added = []
        self.flush_count = 0

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        self.flush_count += 1


class FakeProjectionDatabase:
    def __init__(self):
        self.executions = []
        self.added_batches = []

    async def execute(self, statement, parameters=None):
        self.executions.append((statement, parameters))

    def add_all(self, items):
        self.added_batches.append(list(items))

    async def flush(self):
        return None


def existing_observation(payload, *, status="active"):
    prepared = prepare_memory_entry_payload(payload, stable_id=True)
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    prepared.update(
        status=status,
        valid_to=None,
        last_seen_at=now,
        first_seen_at=now,
        valid_from=now,
    )
    return SimpleNamespace(**prepared)


def test_memory_fingerprint_is_stable_and_evidence_sensitive():
    payload = memory_payload()

    first = build_memory_source_fingerprint(payload)
    second = build_memory_source_fingerprint(dict(payload))
    changed = build_memory_source_fingerprint(memory_payload(evidence_text="Different evidence."))

    assert first == second
    assert len(first) == 64
    assert changed != first
    assert build_memory_entry_id(first) == f"entry_{first[:24]}"


def test_prepare_memory_payload_adds_lifecycle_identity_without_changing_text():
    payload = memory_payload(id=None, evidence_text="  Original   Evidence  ")

    prepared = prepare_memory_entry_payload(payload, stable_id=True)

    assert prepared["id"].startswith("entry_")
    assert prepared["status"] == "active"
    assert prepared["extraction_version"] == "v1"
    assert prepared["confidence"] == 0.7
    assert prepared["evidence_text"] == "  Original   Evidence  "


def test_memory_models_expose_observation_and_governance_tables():
    observation_columns = MemoryEntry.__table__.columns

    for column in (
        "source_fingerprint",
        "extraction_version",
        "status",
        "confidence",
        "first_seen_at",
        "last_seen_at",
        "valid_from",
        "valid_to",
    ):
        assert column in observation_columns

    assert CanonicalMemory.__tablename__ == "canonical_memories"
    assert MemoryRelation.__tablename__ == "memory_relations"
    assert canonical_memory_evidence.name == "canonical_memory_evidence"


def test_memory_migration_extends_the_single_current_head():
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "20260713_01"' in source
    assert 'down_revision = "20260711_01"' in source
    assert '"source_fingerprint"' in source
    assert '"canonical_memories"' in source
    assert '"canonical_memory_evidence"' in source
    assert '"memory_relations"' in source


def test_governance_projection_persists_canonical_evidence_and_relation_rows():
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    first = MemoryEntry(
        **prepare_memory_entry_payload(memory_payload(), stable_id=True),
        created_at=now,
        updated_at=now,
        first_seen_at=now,
        last_seen_at=now,
        valid_from=now,
    )
    second_payload = memory_payload(
        chunk_id="chunk_2",
        summary="The user is studying agent architecture in depth.",
        evidence_text="I am studying agent architecture in depth.",
    )
    second = MemoryEntry(
        **prepare_memory_entry_payload(second_payload, stable_id=True),
        created_at=now,
        updated_at=now,
        first_seen_at=now,
        last_seen_at=now,
        valid_from=now,
    )
    db = FakeProjectionDatabase()

    result = asyncio.run(
        rebuild_memory_governance_projection(
            db,
            user_id=7,
            knowledge_base_id="kb_1",
            knowledge_base_pk=11,
            entries=[first, second],
        )
    )

    canonical_rows = [item for batch in db.added_batches for item in batch if isinstance(item, CanonicalMemory)]
    relation_rows = [item for batch in db.added_batches for item in batch if isinstance(item, MemoryRelation)]
    evidence_parameters = [parameters for _, parameters in db.executions if parameters]

    assert result.canonical_memory_count == 1
    assert result.relation_count == 1
    assert len(canonical_rows) == 1
    assert len(relation_rows) == 1
    assert len(evidence_parameters) == 1
    assert {item["memory_entry_id"] for item in evidence_parameters[0]} == {first.id, second.id}


def test_reconcile_refreshes_an_identical_observation_without_inserting():
    payload = memory_payload()
    existing = existing_observation(payload)
    original_last_seen = existing.last_seen_at
    db = FakeDatabase()

    with (
        patch(
            "app.mneme.domains.memory.service.list_memory_entries_by_document_id",
            AsyncMock(return_value=[existing]),
        ),
        patch(
            "app.mneme.domains.memory.service.list_memory_entries_by_knowledge_base_id",
            AsyncMock(return_value=[existing]),
        ),
        patch(
            "app.mneme.domains.memory.service.rebuild_memory_governance_projection",
            AsyncMock(),
        ) as rebuild_projection,
    ):
        retired_count, active = asyncio.run(
            reconcile_memory_entries_for_document(
                db,
                document=document(),
                entries=[payload],
            )
        )

    assert retired_count == 0
    assert active == [existing]
    assert db.added == []
    assert existing.status == "active"
    assert existing.last_seen_at > original_last_seen
    rebuild_projection.assert_awaited_once()


def test_reconcile_supersedes_missing_observation_and_inserts_changed_evidence():
    old_payload = memory_payload()
    existing = existing_observation(old_payload)
    changed_payload = memory_payload(evidence_text="The user now studies memory governance.")
    db = FakeDatabase()

    with (
        patch(
            "app.mneme.domains.memory.service.list_memory_entries_by_document_id",
            AsyncMock(return_value=[existing]),
        ),
        patch(
            "app.mneme.domains.memory.service.list_memory_entries_by_knowledge_base_id",
            AsyncMock(return_value=[]),
        ),
        patch(
            "app.mneme.domains.memory.service.rebuild_memory_governance_projection",
            AsyncMock(),
        ),
    ):
        retired_count, active = asyncio.run(
            reconcile_memory_entries_for_document(
                db,
                document=document(),
                entries=[changed_payload],
            )
        )

    assert retired_count == 1
    assert existing.status == "superseded"
    assert existing.valid_to is not None
    assert len(db.added) == 1
    assert active == db.added
    assert active[0].id == build_memory_entry_id(active[0].source_fingerprint)
    assert active[0].source_fingerprint != existing.source_fingerprint


def test_memory_queries_and_pipelines_encode_active_and_reconciliation_semantics():
    crud_source = (ROOT / "app/mneme/crud/memory_entry.py").read_text(encoding="utf-8")
    service_source = (ROOT / "app/mneme/domains/memory/service.py").read_text(encoding="utf-8")
    pipeline_source = (ROOT / "app/mneme/pipelines/memory_extract_pipeline.py").read_text(encoding="utf-8")
    resources_source = (ROOT / "app/mneme/domains/documents/resources.py").read_text(encoding="utf-8")

    assert 'MemoryEntry.status == "active"' in crud_source
    assert 'memory_entry_table.c.status == "active"' in crud_source
    assert "delete_memory_entries_by_document_id" not in service_source
    assert "reconcile_memory_entries_for_document" in pipeline_source
    assert "rebuild_memory_governance_projection" in resources_source
