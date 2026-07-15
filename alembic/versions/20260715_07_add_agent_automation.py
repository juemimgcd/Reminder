"""add durable agent automation

Revision ID: 20260715_07
Revises: 20260715_06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260715_07"
down_revision: str | Sequence[str] | None = "20260715_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column("system_managed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "agent_runs",
        sa.Column("run_id", sa.String(length=64), primary_key=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_request_id", sa.String(length=128), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("answer_mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("trigger_type", sa.String(length=32), nullable=False, server_default="user"),
        sa.Column("trigger_id", sa.String(length=64), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("last_event_id", sa.String(length=64), nullable=True),
        sa.Column("queue_wait_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "session_id", "client_request_id", name="uq_agent_runs_request"),
    )
    op.create_index("idx_agent_runs_status_updated", "agent_runs", ["status", "updated_at"])
    op.create_index("idx_agent_runs_trigger", "agent_runs", ["trigger_type", "trigger_id"])

    op.create_table(
        "heartbeat_jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("answer_mode", sa.String(length=32), nullable=False, server_default="general_chat"),
        sa.Column("knowledge_base_id", sa.String(length=64), nullable=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("every_seconds", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("active_timezone", sa.String(length=64), nullable=False, server_default="Asia/Shanghai"),
        sa.Column("active_start", sa.String(length=5), nullable=False, server_default="09:00"),
        sa.Column("active_end", sa.String(length=5), nullable=False, server_default="22:00"),
        sa.Column("isolated_session", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("light_context", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("silent_success", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("event_types", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_id", sa.String(length=64), nullable=True),
        sa.Column("last_status", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_heartbeat_jobs_due", "heartbeat_jobs", ["enabled", "next_run_at"])
    op.create_index("idx_heartbeat_jobs_user", "heartbeat_jobs", ["user_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False, server_default="agent"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("action_url", sa.String(length=500), nullable=True),
        sa.Column("source_run_id", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("idempotency_key", name="uq_notifications_idempotency_key"),
    )
    op.create_index("idx_notifications_user_read", "notifications", ["user_id", "read_at", "created_at"])

    op.create_table(
        "tool_approval_requests",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("action_name", sa.String(length=120), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("action_summary", sa.Text(), nullable=False),
        sa.Column("arguments_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("apply_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("idempotency_key", name="uq_tool_approvals_idempotency_key"),
    )
    op.create_index(
        "idx_tool_approvals_user_status",
        "tool_approval_requests",
        ["user_id", "status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_tool_approvals_user_status", table_name="tool_approval_requests")
    op.drop_table("tool_approval_requests")
    op.drop_index("idx_notifications_user_read", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("idx_heartbeat_jobs_user", table_name="heartbeat_jobs")
    op.drop_index("idx_heartbeat_jobs_due", table_name="heartbeat_jobs")
    op.drop_table("heartbeat_jobs")
    op.drop_index("idx_agent_runs_trigger", table_name="agent_runs")
    op.drop_index("idx_agent_runs_status_updated", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_column("chat_sessions", "system_managed")
