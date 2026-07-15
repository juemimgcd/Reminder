from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.models.base import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("idx_chat_sessions_user_id", "user_id"),
        Index("idx_chat_sessions_knowledge_base_pk", "knowledge_base_pk"),
        CheckConstraint(
            "answer_mode IN ('kb_qa', 'memory_query', 'profile_query', 'analysis_query', 'general_chat')",
            name="ck_chat_sessions_answer_mode",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="会话ID")
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        comment="所属用户ID",
    )
    knowledge_base_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="所属知识库公开ID",
    )
    knowledge_base_pk: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("knowledge_bases.pk"),
        nullable=True,
        comment="所属知识库内部主键",
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="会话标题")

    answer_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="kb_qa", server_default="kb_qa")
    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="message count"
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="last message time"
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="archive time")
    context_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="persisted compacted conversation summary"
    )
    context_summary_through_message_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="last message represented by context summary"
    )
    system_managed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", comment="hidden automation session"
    )

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, knowledge_base_id={self.knowledge_base_id})>"
