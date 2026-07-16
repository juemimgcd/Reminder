from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.memoria.server.models.base import Base


class MemoryRevision(Base):
    __tablename__ = "memory_revisions"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_memory_revisions_valid_interval",
        ),
        UniqueConstraint("revision_id", "memory_id"),
        Index("ix_memory_revisions_owner_scope", "owner_id", "knowledge_base_id"),
        Index(
            "uq_memory_revisions_open_memory",
            "memory_id",
            unique=True,
            postgresql_where=text("valid_to IS NULL"),
        ),
    )

    revision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    memory_id: Mapped[str] = mapped_column(
        ForeignKey("canonical_memories.memory_id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_id: Mapped[int] = mapped_column(nullable=False)
    knowledge_base_id: Mapped[str | None] = mapped_column(String(128))
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    predicate: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(String(128), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
