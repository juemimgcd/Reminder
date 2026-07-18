"""add multi-channel gateway persistence

Revision ID: 20260718_02
Revises: 20260718_01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260718_02"
down_revision: str | Sequence[str] | None = "20260718_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "channel_identities",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("external_user_id", sa.String(length=128), nullable=False),
        sa.Column("mneme_user_id", sa.BigInteger(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["mneme_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_channel_identities_external",
        "channel_identities",
        ["channel", "account_id", "external_user_id"],
        unique=True,
    )
    op.create_index(
        "idx_channel_identities_user",
        "channel_identities",
        ["mneme_user_id"],
    )

    op.create_table(
        "channel_link_codes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("mneme_user_id", sa.BigInteger(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_user_id", sa.String(length=128), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["mneme_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_channel_link_codes_hash",
        "channel_link_codes",
        ["code_hash"],
        unique=True,
    )
    op.create_index(
        "idx_channel_link_codes_user",
        "channel_link_codes",
        ["mneme_user_id", "status"],
    )
    op.create_index(
        "idx_channel_link_codes_expiry",
        "channel_link_codes",
        ["status", "expires_at"],
    )

    op.create_table(
        "channel_conversations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("scope_key", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("external_conversation_id", sa.String(length=128), nullable=False),
        sa.Column("external_thread_id", sa.String(length=128), nullable=True),
        sa.Column("mneme_user_id", sa.BigInteger(), nullable=False),
        sa.Column("chat_session_id", sa.String(length=64), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=64), nullable=True),
        sa.Column("answer_mode", sa.String(length=32), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["chat_session_id"], ["chat_sessions.id"]),
        sa.ForeignKeyConstraint(["mneme_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_channel_conversations_scope",
        "channel_conversations",
        ["scope_key"],
        unique=True,
    )
    op.create_index(
        "idx_channel_conversations_user",
        "channel_conversations",
        ["mneme_user_id"],
    )
    op.create_index(
        "idx_channel_conversations_session",
        "channel_conversations",
        ["chat_session_id"],
    )

    op.create_table(
        "channel_inbound_messages",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("external_message_id", sa.String(length=128), nullable=False),
        sa.Column("external_sender_id", sa.String(length=128), nullable=False),
        sa.Column("external_conversation_id", sa.String(length=128), nullable=False),
        sa.Column("external_thread_id", sa.String(length=128), nullable=True),
        sa.Column("identity_id", sa.String(length=64), nullable=True),
        sa.Column("channel_conversation_id", sa.String(length=64), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("attachments_json", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("agent_run_id", sa.String(length=64), nullable=True),
        sa.Column("rejection_code", sa.String(length=64), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["channel_conversation_id"],
            ["channel_conversations.id"],
        ),
        sa.ForeignKeyConstraint(["identity_id"], ["channel_identities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_channel_inbound_messages_key",
        "channel_inbound_messages",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(
        "idx_channel_inbound_messages_run",
        "channel_inbound_messages",
        ["agent_run_id"],
    )
    op.create_index(
        "idx_channel_inbound_messages_conversation",
        "channel_inbound_messages",
        ["channel_conversation_id"],
    )

    op.create_table(
        "channel_deliveries",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("external_conversation_id", sa.String(length=128), nullable=False),
        sa.Column("external_thread_id", sa.String(length=128), nullable=True),
        sa.Column("reply_to_external_message_id", sa.String(length=128), nullable=True),
        sa.Column("mneme_user_id", sa.BigInteger(), nullable=True),
        sa.Column("inbound_message_id", sa.String(length=64), nullable=True),
        sa.Column("agent_run_id", sa.String(length=64), nullable=True),
        sa.Column("assistant_message_id", sa.String(length=64), nullable=True),
        sa.Column("parts_json", sa.JSON(), nullable=False),
        sa.Column("parts_sent", sa.Integer(), nullable=False),
        sa.Column("external_message_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["assistant_message_id"],
            ["chat_messages.id"],
        ),
        sa.ForeignKeyConstraint(
            ["inbound_message_id"],
            ["channel_inbound_messages.id"],
        ),
        sa.ForeignKeyConstraint(["mneme_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_channel_deliveries_idempotency",
        "channel_deliveries",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(
        "idx_channel_deliveries_dispatch",
        "channel_deliveries",
        ["status", "next_attempt_at"],
    )
    op.create_index(
        "idx_channel_deliveries_run",
        "channel_deliveries",
        ["agent_run_id"],
    )
    op.create_index(
        "idx_channel_deliveries_inbound",
        "channel_deliveries",
        ["inbound_message_id"],
    )


def downgrade() -> None:
    op.drop_table("channel_deliveries")
    op.drop_table("channel_inbound_messages")
    op.drop_table("channel_conversations")
    op.drop_table("channel_link_codes")
    op.drop_table("channel_identities")
