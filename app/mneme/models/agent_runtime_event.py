from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.models.base import Base


class AgentRuntimeEvent(Base):
    __tablename__ = "agent_runtime_events"
    __table_args__ = (
        Index("idx_agent_runtime_events_trace_id", "trace_id"),
        Index("idx_agent_runtime_events_run_id", "run_id"),
        Index("idx_agent_runtime_events_session_id", "session_id"),
        Index("idx_agent_runtime_events_user_id", "user_id"),
        Index("idx_agent_runtime_events_event_type", "event_type"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    loop_index: Mapped[int | None] = mapped_column(nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    selected_capability_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
