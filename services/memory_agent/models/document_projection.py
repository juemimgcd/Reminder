from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from services.memory_agent.models.base import Base


class DocumentProjection(Base):
    __tablename__ = "document_projections"
    __table_args__ = (
        UniqueConstraint("document_id", "document_version"),
        CheckConstraint(
            "status IN ('staging', 'active', 'failed', 'superseded')",
            name="ck_document_projections_status",
        ),
        Index(
            "uq_document_projections_active_document_id",
            "document_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    projection_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    knowledge_base_id: Mapped[str | None] = mapped_column(String(128), index=True)
    document_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    document_version: Mapped[str] = mapped_column(String(128), nullable=False)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    batch_count: Mapped[int] = mapped_column(Integer, nullable=False)
    aggregate_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="staging")
    failure_reason: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
