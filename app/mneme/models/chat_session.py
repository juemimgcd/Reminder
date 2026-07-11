from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.mneme.models.base import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("idx_chat_sessions_user_id", "user_id"),
        Index("idx_chat_sessions_knowledge_base_pk", "knowledge_base_pk"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="会话ID")
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        comment="所属用户ID",
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="所属知识库公开ID",
    )
    knowledge_base_pk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("knowledge_bases.pk"),
        nullable=False,
        comment="所属知识库内部主键",
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="会话标题")

    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0", comment="message count")
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="last message time")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="archive time")

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, knowledge_base_id={self.knowledge_base_id})>"
