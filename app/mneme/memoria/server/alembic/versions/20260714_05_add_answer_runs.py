"""Add persisted answer runs.

Revision ID: 20260714_05
Revises: 20260714_04
Create Date: 2026-07-14

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260714_05"
down_revision: str | Sequence[str] | None = "20260714_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "answer_runs",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=128), nullable=True),
        sa.Column("session_id", sa.String(length=128), nullable=True),
        sa.Column("message_id", sa.String(length=128), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="running", nullable=False),
        sa.Column("current_phase", sa.String(length=16), server_default="validate", nullable=False),
        sa.Column("phase_durations_ms", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expansion_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("confidence", sa.Numeric(precision=9, scale=8), nullable=True),
        sa.Column("uncertainty", sa.Text(), nullable=True),
        sa.Column("insufficient_evidence", sa.Boolean(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("cost", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("retrieval_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generation_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("citations_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "mode IN ('kb_qa', 'memory_query', 'profile_query', 'analysis_query', 'general_chat')",
            name="ck_answer_runs_mode",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_answer_runs_status",
        ),
        sa.CheckConstraint(
            "current_phase IN ('validate', 'retrieve', 'generate', 'citations', 'complete')",
            name="ck_answer_runs_phase",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_answer_runs_confidence",
        ),
        sa.CheckConstraint("expansion_count BETWEEN 0 AND 1", name="ck_answer_runs_expansion_count"),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index(op.f("ix_answer_runs_request_id"), "answer_runs", ["request_id"])
    op.create_index(
        "ix_answer_runs_owner_scope_created",
        "answer_runs",
        ["owner_id", "knowledge_base_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_answer_runs_owner_scope_created", table_name="answer_runs")
    op.drop_index(op.f("ix_answer_runs_request_id"), table_name="answer_runs")
    op.drop_table("answer_runs")
