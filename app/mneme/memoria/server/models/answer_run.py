from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.memoria.server.models.base import Base


class AnswerRun(Base):
    __tablename__ = "answer_runs"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('kb_qa', 'memory_query', 'profile_query', 'analysis_query', 'general_chat')",
            name="ck_answer_runs_mode",
        ),
        CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_answer_runs_status",
        ),
        CheckConstraint(
            "current_phase IN ('validate', 'retrieve', 'generate', 'citations', 'complete')",
            name="ck_answer_runs_phase",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_answer_runs_confidence",
        ),
        CheckConstraint("expansion_count BETWEEN 0 AND 1", name="ck_answer_runs_expansion_count"),
        Index("ix_answer_runs_owner_scope_created", "owner_id", "knowledge_base_id", "created_at"),
        UniqueConstraint("owner_id", "request_id", name="uq_answer_runs_owner_request"),
    )

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False)
    knowledge_base_id: Mapped[str | None] = mapped_column(String(128))
    session_id: Mapped[str | None] = mapped_column(String(128))
    message_id: Mapped[str] = mapped_column(String(128), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="running")
    current_phase: Mapped[str] = mapped_column(String(16), nullable=False, server_default="validate")
    phase_durations_ms: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False, default=dict)
    source_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    expansion_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(9, 8))
    uncertainty: Mapped[str | None] = mapped_column(Text)
    insufficient_evidence: Mapped[bool | None] = mapped_column(Boolean)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    error_code: Mapped[str | None] = mapped_column(String(64))
    response_json: Mapped[dict | None] = mapped_column(JSONB)
    model_attempts: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    selected_provider: Mapped[str | None] = mapped_column(String(64))
    selected_model: Mapped[str | None] = mapped_column(String(255))
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    retrieval_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    generation_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    citations_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
