"""Add staged document projections and vector embeddings.

Revision ID: 20260714_02
Revises: 20260714_01
Create Date: 2026-07-14

"""
from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op
from services.memory_agent.config import settings

revision: str = "20260714_02"
down_revision: str | Sequence[str] | None = "20260714_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "document_projections",
        sa.Column("projection_id", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=128), nullable=False),
        sa.Column("document_id", sa.String(length=128), nullable=False),
        sa.Column("document_version", sa.String(length=128), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("batch_count", sa.Integer(), nullable=False),
        sa.Column("aggregate_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="staging", nullable=False),
        sa.Column("failure_reason", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('staging', 'active', 'failed', 'superseded')",
            name="ck_document_projections_status",
        ),
        sa.PrimaryKeyConstraint("projection_id"),
        sa.UniqueConstraint(
            "owner_id",
            "knowledge_base_id",
            "document_id",
            "document_version",
        ),
    )
    op.create_index(
        op.f("ix_document_projections_document_id"),
        "document_projections",
        ["document_id"],
    )
    op.create_index(
        op.f("ix_document_projections_knowledge_base_id"),
        "document_projections",
        ["knowledge_base_id"],
    )
    op.create_index(
        op.f("ix_document_projections_owner_id"),
        "document_projections",
        ["owner_id"],
    )
    op.create_index(
        "uq_document_projections_active_document_id",
        "document_projections",
        ["owner_id", "knowledge_base_id", "document_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "document_projection_batches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("projection_id", sa.String(length=64), nullable=False),
        sa.Column("batch_index", sa.Integer(), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("chunks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["projection_id"],
            ["document_projections.projection_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("projection_id", "batch_index"),
    )
    op.create_index(
        op.f("ix_document_projection_batches_projection_id"),
        "document_projection_batches",
        ["projection_id"],
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("projection_id", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=128), nullable=False),
        sa.Column("document_id", sa.String(length=128), nullable=False),
        sa.Column("document_version", sa.String(length=128), nullable=False),
        sa.Column("chunk_id", sa.String(length=128), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("page_no", sa.Integer(), nullable=True),
        sa.Column("section_path", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("embedding", Vector(settings.EMBEDDING_DIMENSION), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(
            ["projection_id"],
            ["document_projections.projection_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("projection_id", "chunk_id"),
        sa.UniqueConstraint("projection_id", "chunk_index"),
    )
    op.create_index(
        "ix_document_chunks_active_scope",
        "document_chunks",
        ["owner_id", "knowledge_base_id", "is_active"],
    )
    op.create_index(
        "ix_document_chunks_embedding_hnsw",
        "document_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        op.f("ix_document_chunks_projection_id"),
        "document_chunks",
        ["projection_id"],
    )
    op.create_index(
        "uq_document_chunks_active_chunk_id",
        "document_chunks",
        ["owner_id", "knowledge_base_id", "chunk_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )


def downgrade() -> None:
    op.drop_index("uq_document_chunks_active_chunk_id", table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_projection_id"), table_name="document_chunks")
    op.drop_index("ix_document_chunks_embedding_hnsw", table_name="document_chunks")
    op.drop_index("ix_document_chunks_active_scope", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index(
        op.f("ix_document_projection_batches_projection_id"),
        table_name="document_projection_batches",
    )
    op.drop_table("document_projection_batches")
    op.drop_index(
        "uq_document_projections_active_document_id",
        table_name="document_projections",
    )
    op.drop_index(op.f("ix_document_projections_owner_id"), table_name="document_projections")
    op.drop_index(
        op.f("ix_document_projections_knowledge_base_id"),
        table_name="document_projections",
    )
    op.drop_index(
        op.f("ix_document_projections_document_id"),
        table_name="document_projections",
    )
    op.drop_table("document_projections")
