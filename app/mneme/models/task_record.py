from typing import Optional

from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.models.base import Base


class TaskRecord(Base):
    __tablename__ = "task_records"
    __table_args__ = (
        Index("idx_task_records_target_id", "target_id"),
        Index("idx_task_records_status", "status"),
        Index("idx_task_records_type_status", "task_type", "status"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="task id")
    task_type: Mapped[str] = mapped_column(String(100), nullable=False, comment="task type")
    target_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="target id")
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        comment="task lifecycle status",
    )
    progress_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="progress stage")
    queue_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="queue name")
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="Celery task id")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="attempt count")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3, comment="max attempts")
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="task result summary")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="error message")

    def __repr__(self) -> str:
        return f"<TaskRecord(id={self.id}, task_type='{self.task_type}', status='{self.status}')>"
