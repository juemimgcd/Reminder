from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.memoria.server.models.base import Base


class DocumentProjectionBatch(Base):
    __tablename__ = "document_projection_batches"
    __table_args__ = (UniqueConstraint("projection_id", "batch_index"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    projection_id: Mapped[str] = mapped_column(
        ForeignKey("document_projections.projection_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    batch_index: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    chunks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
