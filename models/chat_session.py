from typing import Optional
from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("idx_chat_sessions_knowledge_base_id", "knowledge_base_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="会话ID")
    knowledge_base_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="所属知识库ID",
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="会话标题")

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, knowledge_base_id={self.knowledge_base_id})>"