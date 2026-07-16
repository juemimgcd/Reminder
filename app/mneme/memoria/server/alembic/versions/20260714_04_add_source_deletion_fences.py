"""Add source deletion fences and document evidence identity.

Revision ID: 20260714_04
Revises: 20260714_03
Create Date: 2026-07-14

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260714_04"
down_revision: str | Sequence[str] | None = "20260714_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "memory_evidence",
        sa.Column("source_document_id", sa.String(length=128), nullable=True),
    )
    op.create_index(
        op.f("ix_memory_evidence_source_document_id"),
        "memory_evidence",
        ["source_document_id"],
    )
    op.create_table(
        "source_deletion_fences",
        sa.Column("fence_key", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=128), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delete_event_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_type IN ('knowledge_base', 'document', 'conversation', 'explicit_request')",
            name="ck_source_deletion_fences_type",
        ),
        sa.PrimaryKeyConstraint("fence_key"),
    )
    op.create_index(
        "ix_source_deletion_fences_owner_scope",
        "source_deletion_fences",
        ["owner_id", "knowledge_base_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_source_deletion_fences_owner_scope",
        table_name="source_deletion_fences",
    )
    op.drop_table("source_deletion_fences")
    op.drop_index(
        op.f("ix_memory_evidence_source_document_id"),
        table_name="memory_evidence",
    )
    op.drop_column("memory_evidence", "source_document_id")
