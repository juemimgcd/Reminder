from datetime import datetime
from typing import Any, Literal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.memoria.server.models.base import Base

MemoryType = Literal["preference", "profile_fact", "project_context", "decision", "goal", "constraint"]
CandidateStatus = Literal["pending", "promoted", "rejected", "expired"]
Sensitivity = Literal["low", "sensitive", "secret"]
MEMORY_TYPES = frozenset(
    {"preference", "profile_fact", "project_context", "decision", "goal", "constraint"}
)


class MemoryCandidate(Base):
    __tablename__ = "memory_candidates"
    __table_args__ = (
        CheckConstraint(
            "memory_type IN ('preference', 'profile_fact', 'project_context', 'decision', 'goal', 'constraint')",
            name="ck_memory_candidates_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'promoted', 'rejected', 'expired')",
            name="ck_memory_candidates_status",
        ),
        CheckConstraint(
            "sensitivity IN ('low', 'sensitive', 'secret')",
            name="ck_memory_candidates_sensitivity",
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_memory_candidates_confidence"),
        ForeignKeyConstraint(
            ["conflicting_revision_id", "conflicting_memory_id"],
            ["memory_revisions.revision_id", "memory_revisions.memory_id"],
            name="fk_memory_candidates_conflicting_revision",
            ondelete="SET NULL",
        ),
        Index("ix_memory_candidates_owner_scope_status", "owner_id", "knowledge_base_id", "status"),
    )

    candidate_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[int] = mapped_column(nullable=False)
    knowledge_base_id: Mapped[str | None] = mapped_column(String(128))
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    predicate: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    sensitivity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")
    extraction_provenance: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    conflicting_memory_id: Mapped[str | None] = mapped_column(String(64))
    conflicting_revision_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
