from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.models.base import Base


class DurableAgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        UniqueConstraint("user_id", "session_id", "client_request_id", name="uq_agent_runs_request"),
        Index("idx_agent_runs_status_updated", "status", "updated_at"),
        Index("idx_agent_runs_trigger", "trigger_type", "trigger_id"),
    )

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    client_request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    answer_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    trigger_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    queue_wait_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class HeartbeatJob(Base):
    __tablename__ = "heartbeat_jobs"
    __table_args__ = (
        Index("idx_heartbeat_jobs_due", "enabled", "next_run_at"),
        Index("idx_heartbeat_jobs_user", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    answer_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="general_chat")
    knowledge_base_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    every_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    active_timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Shanghai")
    active_start: Mapped[str] = mapped_column(String(5), nullable=False, default="09:00")
    active_end: Mapped[str] = mapped_column(String(5), nullable=False, default="22:00")
    isolated_session: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    light_context: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    silent_success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    event_types: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(32), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_notifications_idempotency_key"),
        Index("idx_notifications_user_read", "user_id", "read_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False, default="agent")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    action_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ToolApprovalRequest(Base):
    __tablename__ = "tool_approval_requests"
    __table_args__ = (
        Index("idx_tool_approvals_user_status", "user_id", "status", "created_at"),
        UniqueConstraint("idempotency_key", name="uq_tool_approvals_idempotency_key"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action_name: Mapped[str] = mapped_column(String(120), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    action_summary: Mapped[str] = mapped_column(Text, nullable=False)
    arguments_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    apply_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
