from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from services.memory_agent.models.base import Base


class MemorySettings(Base):
    __tablename__ = "memory_settings"

    owner_id: Mapped[int] = mapped_column(primary_key=True)
    automatic_conversation_memory: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    last_event_occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_event_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
