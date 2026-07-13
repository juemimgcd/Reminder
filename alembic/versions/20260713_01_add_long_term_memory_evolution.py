"""add long-term memory evolution

Revision ID: 20260713_01
Revises: 20260711_01
Create Date: 2026-07-13 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "20260713_01"
down_revision = "20260711_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("memory_entries", sa.Column("source_fingerprint", sa.String(64), nullable=True))
    op.add_column(
        "memory_entries",
        sa.Column("extraction_version", sa.String(32), nullable=False, server_default="v1"),
    )
    op.add_column(
        "memory_entries",
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
    )
    op.add_column(
        "memory_entries",
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
    )
    op.add_column(
        "memory_entries",
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "memory_entries",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "memory_entries",
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("memory_entries", sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE memory_entries
            SET source_fingerprint = md5(concat_ws('|', user_id, knowledge_base_id, document_id,
                                                   chunk_id, entry_type, entry_name, summary, evidence_text))
                                     || md5(concat_ws('|', id, 'legacy-v1')),
                first_seen_at = created_at,
                last_seen_at = created_at,
                valid_from = created_at
            WHERE source_fingerprint IS NULL
            """
        )
    )
    op.alter_column("memory_entries", "source_fingerprint", nullable=False)
    op.alter_column("memory_entries", "first_seen_at", nullable=False, server_default=sa.func.now())
    op.alter_column("memory_entries", "last_seen_at", nullable=False, server_default=sa.func.now())
    op.alter_column("memory_entries", "valid_from", nullable=False, server_default=sa.func.now())
    op.create_index(
        "uq_memory_entries_source_fingerprint",
        "memory_entries",
        ["source_fingerprint"],
        unique=True,
    )
    op.create_index(
        "idx_memory_entries_kb_status",
        "memory_entries",
        ["knowledge_base_pk", "status"],
    )

    op.create_table(
        "canonical_memories",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("knowledge_base_id", sa.String(64), nullable=False),
        sa.Column(
            "knowledge_base_pk",
            sa.BigInteger(),
            sa.ForeignKey("knowledge_bases.pk", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entry_name", sa.String(255), nullable=False),
        sa.Column("entry_type", sa.String(50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("representative_entry_id", sa.String(64), nullable=False),
        sa.Column("evidence_count", sa.BigInteger(), nullable=False),
        sa.Column("document_count", sa.BigInteger(), nullable=False),
        sa.Column("importance_score", sa.Float(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_canonical_memories_kb_status", "canonical_memories", ["knowledge_base_pk", "status"])
    op.create_index("idx_canonical_memories_user_id", "canonical_memories", ["user_id"])

    op.create_table(
        "canonical_memory_evidence",
        sa.Column(
            "canonical_memory_id",
            sa.String(64),
            sa.ForeignKey("canonical_memories.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "memory_entry_id",
            sa.String(64),
            sa.ForeignKey("memory_entries.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "memory_relations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("knowledge_base_id", sa.String(64), nullable=False),
        sa.Column(
            "knowledge_base_pk",
            sa.BigInteger(),
            sa.ForeignKey("knowledge_bases.pk", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_entry_id",
            sa.String(64),
            sa.ForeignKey("memory_entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_entry_id",
            sa.String(64),
            sa.ForeignKey("memory_entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relation_type", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_memory_relations_knowledge_base_pk", "memory_relations", ["knowledge_base_pk"])


def downgrade() -> None:
    op.drop_index("idx_memory_relations_knowledge_base_pk", table_name="memory_relations")
    op.drop_table("memory_relations")
    op.drop_table("canonical_memory_evidence")
    op.drop_index("idx_canonical_memories_user_id", table_name="canonical_memories")
    op.drop_index("idx_canonical_memories_kb_status", table_name="canonical_memories")
    op.drop_table("canonical_memories")

    op.drop_index("idx_memory_entries_kb_status", table_name="memory_entries")
    op.drop_index("uq_memory_entries_source_fingerprint", table_name="memory_entries")
    for column in (
        "valid_to",
        "valid_from",
        "last_seen_at",
        "first_seen_at",
        "confidence",
        "status",
        "extraction_version",
        "source_fingerprint",
    ):
        op.drop_column("memory_entries", column)
