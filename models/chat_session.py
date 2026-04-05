from typing import Optional
from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("idx_chat_sessions_user_id", "user_id"),
        Index("idx_chat_sessions_knowledge_base_id", "knowledge_base_id"),
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
        ForeignKey("knowledge_bases.id"),
        nullable=False,
        comment="所属知识库ID",
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="会话标题")

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, knowledge_base_id={self.knowledge_base_id})>"
