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


def test_document_folder_knowledge_base_fk_cascades_without_weakening_parent_fk():
    foreign_keys = {
        foreign_key.parent.name: foreign_key
        for foreign_key in DocumentFolder.__table__.foreign_keys
    }

    knowledge_base_fk = foreign_keys["knowledge_base_pk"]
    assert knowledge_base_fk.target_fullname == "knowledge_bases.pk"
    assert knowledge_base_fk.ondelete == "CASCADE"

    parent_fk = foreign_keys["parent_pk"]
    assert parent_fk.target_fullname == "document_folders.pk"
    assert parent_fk.deferrable is True
    assert parent_fk.initially == "DEFERRED"
    assert parent_fk.ondelete is None
    assert DocumentFolder.__table__.c.parent_pk.nullable is False


def test_workspace_migration_cascades_folder_cleanup_with_knowledge_base_deletion():
    source = Path("alembic/versions/20260711_01_add_document_workspace.py").read_text("utf-8")
    assert 'sa.ForeignKey("knowledge_bases.pk", ondelete="CASCADE")' in source
    assert (
        'sa.ForeignKey("document_folders.pk", deferrable=True, initially="DEFERRED")'
        in source
    )
