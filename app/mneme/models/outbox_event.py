from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.models.base import Base


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        Index("idx_outbox_events_status_next_attempt", "status", "next_attempt_at"),
        Index("idx_outbox_events_backend_status", "target_backend", "status"),
        Index("idx_outbox_events_aggregate", "aggregate_type", "aggregate_id"),
        Index("idx_outbox_events_idempotency_key", "idempotency_key", unique=True),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="Outbox event ID")
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, comment="Event type")
    aggregate_type: Mapped[str] = mapped_column(String(80), nullable=False, comment="Aggregate type")
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="Aggregate ID")
    target_backend: Mapped[str] = mapped_column(String(50), nullable=False, comment="Target projection backend")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, comment="Event payload")
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False, comment="Idempotency key")
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        comment="Outbox lifecycle status",
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Attempt count")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3, comment="Max attempts")
    enqueued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Immutable event enqueue time",
    )
    next_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Next eligible dispatch time",
    )
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="Lock time")
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Processed time"
    )
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Last error")

    def __repr__(self) -> str:
        return (
            f"<OutboxEvent(id={self.id}, event_type='{self.event_type}', "
            f"target_backend='{self.target_backend}', status='{self.status}')>"
        )
