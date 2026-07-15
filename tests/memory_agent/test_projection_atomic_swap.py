from pathlib import Path

from services.memory_agent.services.projections import _snapshot_hash


def test_projection_snapshot_hash_changes_when_chunk_order_changes():
    first = [{"chunk_id": "a", "chunk_index": 0, "content": "one", "content_hash": "h1"}]
    second = [{"chunk_id": "b", "chunk_index": 1, "content": "two", "content_hash": "h2"}]

    assert _snapshot_hash(first + second) != _snapshot_hash(second + first)


def test_finalize_uses_a_database_lock_and_only_deactivates_old_version_at_swap():
    source = Path("services/memory_agent/services/projections.py").read_text(encoding="utf-8")

    assert "pg_advisory_lock" in source
    assert "old_projection.status = \"superseded\"" in source
    assert "DocumentChunk).where(DocumentChunk.projection_id.in_(old_projection_ids))" in source
    assert "projection.status = \"active\"" in source
    assert source.index("old_projection.status = \"superseded\"") < source.index("projection.status = \"active\"")


def test_projection_model_keeps_one_active_version_per_document_scope():
    from services.memory_agent.models.document_projection import DocumentProjection

    indexes = {index.name: index for index in DocumentProjection.__table__.indexes}
    active = indexes["uq_document_projections_active_document_id"]

    assert active.unique
    assert "status = 'active'" in str(active.dialect_options["postgresql"]["where"])
