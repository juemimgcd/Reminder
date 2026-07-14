from datetime import datetime
from typing import Literal

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from services.memory_agent.models.base import Base

MemoryStatus = Literal["active", "superseded", "invalidated"]


class CanonicalMemory(Base):
    __tablename__ = "canonical_memories"
    __table_args__ = (
        CheckConstraint(
            "memory_type IN ('preference', 'profile_fact', 'project_context', 'decision', 'goal', 'constraint')",
            name="ck_canonical_memories_type",
        ),
        CheckConstraint(
            "status IN ('active', 'superseded', 'invalidated')",
            name="ck_canonical_memories_status",
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_canonical_memories_confidence"),
        Index("ix_canonical_memories_owner_scope_status", "owner_id", "knowledge_base_id", "status"),
        Index(
            "uq_canonical_memories_active_kb_fingerprint",
            "owner_id",
            "knowledge_base_id",
            "fingerprint",
            unique=True,
            postgresql_where=text("status = 'active' AND knowledge_base_id IS NOT NULL"),
        ),
        Index(
            "uq_canonical_memories_active_global_fingerprint",
            "owner_id",
            "fingerprint",
            unique=True,
            postgresql_where=text("status = 'active' AND knowledge_base_id IS NULL"),
        ),
    )

    memory_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[int] = mapped_column(nullable=False)
    knowledge_base_id: Mapped[str | None] = mapped_column(String(128))
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    predicate: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    retrieval_weight: Mapped[float] = mapped_column(Float, nullable=False, server_default="1")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")
    active_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("memory_revisions.revision_id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
