"""add document workspace persistence

Revision ID: 20260711_01
Revises: 20260526_03, 20260707_02
Create Date: 2026-07-11 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "20260711_01"
down_revision = ("20260526_03", "20260707_02")
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "document_folders",
        sa.Column("pk", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("id", sa.String(64), nullable=False, unique=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("knowledge_base_id", sa.String(64), nullable=False),
        sa.Column("knowledge_base_pk", sa.BigInteger(), sa.ForeignKey("knowledge_bases.pk"), nullable=False),
        sa.Column(
            "parent_pk",
            sa.BigInteger(),
            sa.ForeignKey("document_folders.pk", deferrable=True, initially="DEFERRED"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("normalized_name", sa.String(255), nullable=False),
        sa.Column("is_root", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "knowledge_base_pk",
            "parent_pk",
            "normalized_name",
            name="uq_document_folders_parent_name",
        ),
    )
    op.create_index(
        "idx_document_folders_kb_parent",
        "document_folders",
        ["knowledge_base_pk", "parent_pk"],
    )
    op.create_index(
        "uq_document_folders_kb_root",
        "document_folders",
        ["knowledge_base_pk"],
        unique=True,
        postgresql_where=sa.text("is_root"),
    )
    op.add_column("documents", sa.Column("folder_pk", sa.BigInteger(), nullable=True))
    op.add_column("documents", sa.Column("content_sha256", sa.String(64), nullable=True))
    op.add_column(
        "documents",
        sa.Column("normalized_file_name", sa.String(255), nullable=False, server_default=""),
    )
    op.add_column(
        "documents",
        sa.Column("version_group_id", sa.String(64), nullable=False, server_default=""),
    )
    op.add_column(
        "documents",
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("documents", sa.Column("previous_document_id", sa.String(64), nullable=True))
    op.add_column("documents", sa.Column("duplicate_of_document_id", sa.String(64), nullable=True))
    op.create_foreign_key(
        "fk_documents_folder_pk",
        "documents",
        "document_folders",
        ["folder_pk"],
        ["pk"],
    )
    op.execute(sa.text("""
        INSERT INTO document_folders
            (id, user_id, knowledge_base_id, knowledge_base_pk, parent_pk, name, normalized_name, is_root)
        SELECT
            'fld_root_' || substr(md5(id), 1, 24), user_id, id, pk, NULL, '/', '/', TRUE
        FROM knowledge_bases
    """))
    op.execute(sa.text("UPDATE document_folders SET parent_pk = pk WHERE is_root"))
    op.execute(sa.text("""
        UPDATE documents AS d
        SET folder_pk = f.pk,
            normalized_file_name = lower(btrim(d.file_name)),
            version_group_id = d.id,
            version_number = 1
        FROM document_folders AS f
        WHERE f.knowledge_base_pk = d.knowledge_base_pk AND f.is_root
    """))
    op.alter_column("document_folders", "parent_pk", nullable=False)
    op.alter_column("documents", "folder_pk", nullable=False)
    op.create_index(
        "uq_documents_kb_canonical_sha256",
        "documents",
        ["knowledge_base_pk", "content_sha256"],
        unique=True,
        postgresql_where=sa.text("content_sha256 IS NOT NULL AND duplicate_of_document_id IS NULL"),
    )


def downgrade():
    op.drop_index("uq_documents_kb_canonical_sha256", table_name="documents")
    op.drop_constraint("fk_documents_folder_pk", "documents", type_="foreignkey")
    for column in (
        "duplicate_of_document_id",
        "previous_document_id",
        "version_number",
        "version_group_id",
        "normalized_file_name",
        "content_sha256",
        "folder_pk",
    ):
        op.drop_column("documents", column)
    op.drop_index("uq_document_folders_kb_root", table_name="document_folders")
    op.drop_index("idx_document_folders_kb_parent", table_name="document_folders")
    op.drop_table("document_folders")
