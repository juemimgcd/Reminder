"""Add governed memory evidence, candidates, revisions, and settings.

Revision ID: 20260714_03
Revises: 20260714_02
Create Date: 2026-07-14

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260714_03"
down_revision: str | Sequence[str] | None = "20260714_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memory_evidence",
        sa.Column("evidence_id", sa.String(length=64), nullable=False),
        sa.Column("identity_hash", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=128), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("source_version", sa.String(length=128), nullable=False),
        sa.Column("minimum_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("evidence_id"),
        sa.UniqueConstraint("identity_hash"),
    )
    op.create_index(
        "ix_memory_evidence_owner_scope",
        "memory_evidence",
        ["owner_id", "knowledge_base_id"],
    )

    op.create_table(
        "memory_settings",
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column(
            "automatic_conversation_memory",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("owner_id"),
    )

    # active_revision_id is added after memory_revisions to resolve the intentional FK cycle.
    op.create_table(
        "canonical_memories",
        sa.Column("memory_id", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=128), nullable=True),
        sa.Column("memory_type", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("predicate", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("retrieval_weight", sa.Float(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("active_revision_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "memory_type IN ('preference', 'profile_fact', 'project_context', 'decision', 'goal', 'constraint')",
            name="ck_canonical_memories_type",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'superseded', 'invalidated')",
            name="ck_canonical_memories_status",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_canonical_memories_confidence",
        ),
        sa.PrimaryKeyConstraint("memory_id"),
    )
    op.create_index(
        "ix_canonical_memories_owner_scope_status",
        "canonical_memories",
        ["owner_id", "knowledge_base_id", "status"],
    )
    op.create_index(
        "uq_canonical_memories_active_kb_fingerprint",
        "canonical_memories",
        ["owner_id", "knowledge_base_id", "fingerprint"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND knowledge_base_id IS NOT NULL"),
    )
    op.create_index(
        "uq_canonical_memories_active_global_fingerprint",
        "canonical_memories",
        ["owner_id", "fingerprint"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND knowledge_base_id IS NULL"),
    )

    op.create_table(
        "memory_revisions",
        sa.Column("revision_id", sa.String(length=64), nullable=False),
        sa.Column("memory_id", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=128), nullable=True),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("predicate", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.String(length=128), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_memory_revisions_valid_interval",
        ),
        sa.ForeignKeyConstraint(["memory_id"], ["canonical_memories.memory_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("revision_id"),
        sa.UniqueConstraint("revision_id", "memory_id"),
    )
    op.create_index(
        op.f("ix_memory_revisions_memory_id"),
        "memory_revisions",
        ["memory_id"],
    )
    op.create_index(
        "ix_memory_revisions_owner_scope",
        "memory_revisions",
        ["owner_id", "knowledge_base_id"],
    )
    op.create_index(
        "uq_memory_revisions_open_memory",
        "memory_revisions",
        ["memory_id"],
        unique=True,
        postgresql_where=sa.text("valid_to IS NULL"),
    )
    op.create_foreign_key(
        "fk_canonical_memories_active_revision",
        "canonical_memories",
        "memory_revisions",
        ["active_revision_id", "memory_id"],
        ["revision_id", "memory_id"],
        deferrable=True,
        initially="DEFERRED",
    )

    op.create_table(
        "memory_candidates",
        sa.Column("candidate_id", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=128), nullable=True),
        sa.Column("memory_type", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("predicate", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("sensitivity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("extraction_provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("conflicting_memory_id", sa.String(length=64), nullable=True),
        sa.Column("conflicting_revision_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "memory_type IN ('preference', 'profile_fact', 'project_context', 'decision', 'goal', 'constraint')",
            name="ck_memory_candidates_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'promoted', 'rejected', 'expired')",
            name="ck_memory_candidates_status",
        ),
        sa.CheckConstraint(
            "sensitivity IN ('low', 'sensitive', 'secret')",
            name="ck_memory_candidates_sensitivity",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_memory_candidates_confidence",
        ),
        sa.ForeignKeyConstraint(
            ["conflicting_revision_id", "conflicting_memory_id"],
            ["memory_revisions.revision_id", "memory_revisions.memory_id"],
            name="fk_memory_candidates_conflicting_revision",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("candidate_id"),
    )
    op.create_index(
        "ix_memory_candidates_owner_scope_status",
        "memory_candidates",
        ["owner_id", "knowledge_base_id", "status"],
    )

    op.create_table(
        "memory_relations",
        sa.Column("relation_id", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=128), nullable=True),
        sa.Column("source_memory_id", sa.String(length=64), nullable=False),
        sa.Column("target_memory_id", sa.String(length=64), nullable=False),
        sa.Column("relation_type", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "source_memory_id <> target_memory_id",
            name="ck_memory_relations_distinct_memories",
        ),
        sa.ForeignKeyConstraint(
            ["source_memory_id"], ["canonical_memories.memory_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_memory_id"], ["canonical_memories.memory_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("relation_id"),
        sa.UniqueConstraint("owner_id", "source_memory_id", "target_memory_id", "relation_type"),
    )
    op.create_index(
        "ix_memory_relations_owner_scope",
        "memory_relations",
        ["owner_id", "knowledge_base_id"],
    )

    op.create_table(
        "memory_candidate_evidence",
        sa.Column("candidate_id", sa.String(length=64), nullable=False),
        sa.Column("evidence_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["memory_candidates.candidate_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"], ["memory_evidence.evidence_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("candidate_id", "evidence_id"),
    )
    op.create_table(
        "memory_revision_evidence",
        sa.Column("revision_id", sa.String(length=64), nullable=False),
        sa.Column("evidence_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["revision_id"], ["memory_revisions.revision_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"], ["memory_evidence.evidence_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("revision_id", "evidence_id"),
    )


def downgrade() -> None:
    op.drop_table("memory_revision_evidence")
    op.drop_table("memory_candidate_evidence")
    op.drop_index("ix_memory_relations_owner_scope", table_name="memory_relations")
    op.drop_table("memory_relations")
    op.drop_index("ix_memory_candidates_owner_scope_status", table_name="memory_candidates")
    op.drop_table("memory_candidates")
    op.drop_constraint(
        "fk_canonical_memories_active_revision",
        "canonical_memories",
        type_="foreignkey",
    )
    op.drop_index("uq_memory_revisions_open_memory", table_name="memory_revisions")
    op.drop_index("ix_memory_revisions_owner_scope", table_name="memory_revisions")
    op.drop_index(op.f("ix_memory_revisions_memory_id"), table_name="memory_revisions")
    op.drop_table("memory_revisions")
    op.drop_index(
        "uq_canonical_memories_active_global_fingerprint",
        table_name="canonical_memories",
    )
    op.drop_index(
        "uq_canonical_memories_active_kb_fingerprint",
        table_name="canonical_memories",
    )
    op.drop_index("ix_canonical_memories_owner_scope_status", table_name="canonical_memories")
    op.drop_table("canonical_memories")
    op.drop_table("memory_settings")
    op.drop_index("ix_memory_evidence_owner_scope", table_name="memory_evidence")
    op.drop_table("memory_evidence")
