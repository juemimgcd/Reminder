from typing import Optional

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


# 表达异步任务在数据库中的持久化状态记录。
class TaskRecord(Base):
    __tablename__ = "task_records"
    __table_args__ = (
        Index("idx_task_records_target_id", "target_id"),
        Index("idx_task_records_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="任务ID")
    task_type: Mapped[str] = mapped_column(String(100), nullable=False, comment="任务类型")
    target_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="目标对象ID")
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="queued",
        comment="任务状态",
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")

    def __repr__(self) -> str:
        return f"<TaskRecord(id={self.id}, task_type='{self.task_type}', status='{self.status}')>"
