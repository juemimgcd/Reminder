from sqlalchemy import JSON, BigInteger, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.models.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("idx_chat_messages_session_id", "session_id"),
        Index("idx_chat_messages_user_id", "user_id"),
        Index("idx_chat_messages_knowledge_base_pk", "knowledge_base_pk"),
        Index("idx_chat_messages_agent_run_id", "agent_run_id"),
        UniqueConstraint("agent_run_id", "role", name="uq_chat_messages_agent_run_role"),
        UniqueConstraint("session_id", "sequence_no", name="uq_chat_messages_session_sequence"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="message id")
    session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("chat_sessions.id"),
        nullable=False,
        comment="chat session id",
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        comment="owner user id",
    )
    knowledge_base_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="knowledge base public id")
    knowledge_base_pk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("knowledge_bases.pk"),
        nullable=False,
        comment="knowledge base internal id",
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, comment="user or assistant")
    agent_run_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="idempotent agent run identifier"
    )
    sequence_no: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="stable message order within a chat session"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="message content")
    sources_json: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="chat sources")
    citations_json: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="chat citations")
    tool_calls_json: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="agent tool evidence")
    route_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="query route")
    model_config_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="AI model config id")
