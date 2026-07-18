from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.models.base import Base


class ChannelIdentity(Base):
    __tablename__ = "channel_identities"
    __table_args__ = (
        Index(
            "uq_channel_identities_external",
            "channel",
            "account_id",
            "external_user_id",
            unique=True,
        ),
        Index("idx_channel_identities_user", "mneme_user_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    mneme_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ChannelLinkCode(Base):
    __tablename__ = "channel_link_codes"
    __table_args__ = (
        Index("uq_channel_link_codes_hash", "code_hash", unique=True),
        Index("idx_channel_link_codes_user", "mneme_user_id", "status"),
        Index("idx_channel_link_codes_expiry", "status", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    mneme_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class ChannelConversation(Base):
    __tablename__ = "channel_conversations"
    __table_args__ = (
        Index("uq_channel_conversations_scope", "scope_key", unique=True),
        Index("idx_channel_conversations_user", "mneme_user_id"),
        Index("idx_channel_conversations_session", "chat_session_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scope_key: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_conversation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_thread_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mneme_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )
    chat_session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("chat_sessions.id"),
        nullable=False,
    )
    knowledge_base_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    answer_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="general_chat",
    )


class ChannelInboundMessage(Base):
    __tablename__ = "channel_inbound_messages"
    __table_args__ = (
        Index("uq_channel_inbound_messages_key", "idempotency_key", unique=True),
        Index("idx_channel_inbound_messages_run", "agent_run_id"),
        Index("idx_channel_inbound_messages_conversation", "channel_conversation_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_message_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_sender_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_conversation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_thread_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    identity_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("channel_identities.id"),
        nullable=True,
    )
    channel_conversation_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("channel_conversations.id"),
        nullable=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    attachments_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="received")
    agent_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rejection_code: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ChannelDelivery(Base):
    __tablename__ = "channel_deliveries"
    __table_args__ = (
        Index("uq_channel_deliveries_idempotency", "idempotency_key", unique=True),
        Index("idx_channel_deliveries_dispatch", "status", "next_attempt_at"),
        Index("idx_channel_deliveries_run", "agent_run_id"),
        Index("idx_channel_deliveries_inbound", "inbound_message_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_conversation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_thread_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reply_to_external_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mneme_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=True,
    )
    inbound_message_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("channel_inbound_messages.id"),
        nullable=True,
    )
    agent_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    assistant_message_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("chat_messages.id"),
        nullable=True,
    )
    parts_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    parts_sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    external_message_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
