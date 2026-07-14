from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from services.memory_agent.models.base import Base


class MemoryRelation(Base):
    __tablename__ = "memory_relations"
    __table_args__ = (
        UniqueConstraint("owner_id", "source_memory_id", "target_memory_id", "relation_type"),
        CheckConstraint("source_memory_id <> target_memory_id", name="ck_memory_relations_distinct_memories"),
        Index("ix_memory_relations_owner_scope", "owner_id", "knowledge_base_id"),
    )

    relation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[int] = mapped_column(nullable=False)
    knowledge_base_id: Mapped[str | None] = mapped_column(String(128))
    source_memory_id: Mapped[str] = mapped_column(
        ForeignKey("canonical_memories.memory_id", ondelete="CASCADE"), nullable=False
    )
    target_memory_id: Mapped[str] = mapped_column(
        ForeignKey("canonical_memories.memory_id", ondelete="CASCADE"), nullable=False
    )
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
