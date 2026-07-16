from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.memoria.server.models.base import Base


class SourceDeletionFence(Base):
    __tablename__ = "source_deletion_fences"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('knowledge_base', 'document', 'conversation', 'explicit_request')",
            name="ck_source_deletion_fences_type",
        ),
        Index(
            "ix_source_deletion_fences_owner_scope",
            "owner_id",
            "knowledge_base_id",
        ),
    )

    fence_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[int] = mapped_column(nullable=False)
    knowledge_base_id: Mapped[str | None] = mapped_column(String(128))
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delete_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
