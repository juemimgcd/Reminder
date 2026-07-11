from pathlib import Path

from app.mneme.models.document import Document
from app.mneme.models.document_folder import DocumentFolder


def test_document_workspace_models_expose_folder_hash_and_version_fields():
    assert DocumentFolder.__tablename__ == "document_folders"
    for name in {
        "folder_pk", "content_sha256", "normalized_file_name",
        "version_group_id", "version_number", "previous_document_id",
        "duplicate_of_document_id",
    }:
        assert hasattr(Document, name)


def test_workspace_migration_merges_heads_and_defines_canonical_hash_index():
    source = Path("alembic/versions/20260711_01_add_document_workspace.py").read_text("utf-8")
    assert 'down_revision = ("20260526_03", "20260707_02")' in source
    assert "uq_documents_kb_canonical_sha256" in source
    assert "duplicate_of_document_id IS NULL" in source
