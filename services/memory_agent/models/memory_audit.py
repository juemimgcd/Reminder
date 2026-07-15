from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from services.memory_agent.models.base import Base


class MemoryActionAudit(Base):
    __tablename__ = "memory_action_audit"
    __table_args__ = (Index("ix_memory_action_audit_scope_created", "owner_id", "knowledge_base_id", "created_at"),)

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False)
    knowledge_base_id: Mapped[str | None] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
