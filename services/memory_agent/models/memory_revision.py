from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from services.memory_agent.models.base import Base


class MemoryRevision(Base):
    __tablename__ = "memory_revisions"
    __table_args__ = (Index("ix_memory_revisions_owner_scope", "owner_id", "knowledge_base_id"),)

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
