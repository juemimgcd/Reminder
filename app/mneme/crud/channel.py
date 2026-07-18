from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.models.channel import (
    ChannelConversation,
    ChannelDelivery,
    ChannelIdentity,
    ChannelInboundMessage,
    ChannelLinkCode,
)


async def create_channel_link_code(
    db: AsyncSession,
    *,
    link_id: str,
    channel: str,
    account_id: str,
    mneme_user_id: int,
    code_hash: str,
    expires_at: datetime,
) -> ChannelLinkCode:
    link = ChannelLinkCode(
        id=link_id,
        channel=channel,
        account_id=account_id,
        mneme_user_id=mneme_user_id,
        code_hash=code_hash,
        expires_at=expires_at,
        status="pending",
    )
    db.add(link)
    await db.flush()
    return link


async def consume_channel_link_code(
    db: AsyncSession,
    *,
    code_hash: str,
    channel: str,
    account_id: str,
    external_user_id: str,
    now: datetime,
) -> ChannelLinkCode | None:
    link = await db.scalar(
        select(ChannelLinkCode)
        .where(
            ChannelLinkCode.code_hash == code_hash,
            ChannelLinkCode.channel == channel,
            ChannelLinkCode.account_id == account_id,
            ChannelLinkCode.status == "pending",
            ChannelLinkCode.expires_at > now,
        )
        .with_for_update()
    )
    if link is None:
        return None
    link.status = "used"
    link.used_at = now
    link.external_user_id = external_user_id
    await db.flush()
    return link


async def get_channel_identity(
    db: AsyncSession,
    *,
    channel: str,
    account_id: str,
    external_user_id: str,
) -> ChannelIdentity | None:
    return await db.scalar(
        select(ChannelIdentity).where(
            ChannelIdentity.channel == channel,
            ChannelIdentity.account_id == account_id,
            ChannelIdentity.external_user_id == external_user_id,
        )
    )


async def create_channel_identity(
    db: AsyncSession,
    *,
    identity_id: str,
    channel: str,
    account_id: str,
    external_user_id: str,
    mneme_user_id: int,
    verified_at: datetime,
    metadata: dict[str, Any],
) -> ChannelIdentity:
    identity = ChannelIdentity(
        id=identity_id,
        channel=channel,
        account_id=account_id,
        external_user_id=external_user_id,
        mneme_user_id=mneme_user_id,
        verified_at=verified_at,
        status="active",
        metadata_json=metadata,
    )
    db.add(identity)
    await db.flush()
    return identity


async def list_channel_identities(
    db: AsyncSession,
    *,
    mneme_user_id: int,
) -> list[ChannelIdentity]:
    result = await db.execute(
        select(ChannelIdentity)
        .where(ChannelIdentity.mneme_user_id == mneme_user_id)
        .order_by(ChannelIdentity.created_at.desc())
    )
    return list(result.scalars())


async def create_or_get_channel_inbound(
    db: AsyncSession,
    *,
    values: dict[str, Any],
) -> tuple[ChannelInboundMessage, bool]:
    created = (
        await db.execute(
            insert(ChannelInboundMessage)
            .values(**values)
            .on_conflict_do_nothing(
                index_elements=[ChannelInboundMessage.idempotency_key]
            )
            .returning(ChannelInboundMessage)
        )
    ).scalar_one_or_none()
    if created is not None:
        return created, True
    existing = await db.scalar(
        select(ChannelInboundMessage).where(
            ChannelInboundMessage.idempotency_key == values["idempotency_key"]
        )
    )
    if existing is None:
        raise RuntimeError("channel inbound idempotency row could not be loaded")
    return existing, False


async def get_channel_conversation_by_scope(
    db: AsyncSession,
    *,
    scope_key: str,
) -> ChannelConversation | None:
    return await db.scalar(
        select(ChannelConversation).where(ChannelConversation.scope_key == scope_key)
    )


async def create_channel_conversation(
    db: AsyncSession,
    *,
    conversation_id: str,
    scope_key: str,
    channel: str,
    account_id: str,
    external_conversation_id: str,
    external_thread_id: str | None,
    mneme_user_id: int,
    chat_session_id: str,
) -> ChannelConversation:
    conversation = ChannelConversation(
        id=conversation_id,
        scope_key=scope_key,
        channel=channel,
        account_id=account_id,
        external_conversation_id=external_conversation_id,
        external_thread_id=external_thread_id,
        mneme_user_id=mneme_user_id,
        chat_session_id=chat_session_id,
        answer_mode="general_chat",
    )
    db.add(conversation)
    await db.flush()
    return conversation


async def get_channel_conversation(
    db: AsyncSession,
    *,
    conversation_id: str,
    mneme_user_id: int | None = None,
) -> ChannelConversation | None:
    query = select(ChannelConversation).where(
        ChannelConversation.id == conversation_id
    )
    if mneme_user_id is not None:
        query = query.where(ChannelConversation.mneme_user_id == mneme_user_id)
    return await db.scalar(query)


async def list_channel_conversations(
    db: AsyncSession,
    *,
    mneme_user_id: int,
) -> list[ChannelConversation]:
    result = await db.execute(
        select(ChannelConversation)
        .where(ChannelConversation.mneme_user_id == mneme_user_id)
        .order_by(ChannelConversation.created_at.desc())
    )
    return list(result.scalars())


async def list_channel_deliveries(
    db: AsyncSession,
    *,
    mneme_user_id: int,
    limit: int = 50,
) -> list[ChannelDelivery]:
    result = await db.execute(
        select(ChannelDelivery)
        .where(ChannelDelivery.mneme_user_id == mneme_user_id)
        .order_by(ChannelDelivery.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars())


async def create_or_get_channel_delivery(
    db: AsyncSession,
    *,
    values: dict[str, Any],
) -> tuple[ChannelDelivery, bool]:
    created = (
        await db.execute(
            insert(ChannelDelivery)
            .values(**values)
            .on_conflict_do_nothing(
                index_elements=[ChannelDelivery.idempotency_key]
            )
            .returning(ChannelDelivery)
        )
    ).scalar_one_or_none()
    if created is not None:
        return created, True
    existing = await db.scalar(
        select(ChannelDelivery).where(
            ChannelDelivery.idempotency_key == values["idempotency_key"]
        )
    )
    if existing is None:
        raise RuntimeError("channel delivery idempotency row could not be loaded")
    return existing, False


async def list_dispatchable_channel_deliveries(
    db: AsyncSession,
    *,
    now: datetime,
    limit: int,
) -> list[ChannelDelivery]:
    result = await db.execute(
        select(ChannelDelivery)
        .where(
            ChannelDelivery.status.in_(("pending", "failed")),
            (
                ChannelDelivery.next_attempt_at.is_(None)
                | (ChannelDelivery.next_attempt_at <= now)
            ),
        )
        .order_by(ChannelDelivery.created_at)
        .limit(limit)
    )
    return list(result.scalars())


async def recover_stale_channel_deliveries(
    db: AsyncSession,
    *,
    stale_before: datetime,
    now: datetime,
) -> int:
    result = await db.execute(
        update(ChannelDelivery)
        .where(
            ChannelDelivery.status == "running",
            ChannelDelivery.locked_at < stale_before,
        )
        .values(
            status="failed",
            locked_at=None,
            next_attempt_at=now,
            last_error="channel delivery lease expired",
        )
    )
    return result.rowcount or 0


async def claim_channel_delivery(
    db: AsyncSession,
    *,
    delivery_id: str,
    now: datetime,
) -> ChannelDelivery | None:
    delivery = await db.scalar(
        select(ChannelDelivery)
        .where(ChannelDelivery.id == delivery_id)
        .with_for_update(skip_locked=True)
    )
    if delivery is None or delivery.status not in {"pending", "failed"}:
        return None
    if delivery.next_attempt_at is not None and delivery.next_attempt_at > now:
        return None
    delivery.status = "running"
    delivery.attempt_count += 1
    delivery.locked_at = now
    delivery.last_error = None
    await db.flush()
    return delivery


async def retry_channel_delivery(
    db: AsyncSession,
    *,
    delivery_id: str,
    mneme_user_id: int,
) -> ChannelDelivery | None:
    delivery = await db.scalar(
        select(ChannelDelivery)
        .where(
            ChannelDelivery.id == delivery_id,
            ChannelDelivery.mneme_user_id == mneme_user_id,
        )
        .with_for_update()
    )
    if delivery is None:
        return None
    if delivery.status == "succeeded":
        return delivery
    delivery.status = "pending"
    delivery.attempt_count = 0
    delivery.next_attempt_at = None
    delivery.locked_at = None
    delivery.processed_at = None
    delivery.last_error = None
    await db.flush()
    return delivery


async def get_channel_inbound_by_run_id(
    db: AsyncSession,
    *,
    agent_run_id: str,
) -> ChannelInboundMessage | None:
    return await db.scalar(
        select(ChannelInboundMessage).where(
            ChannelInboundMessage.agent_run_id == agent_run_id
        )
    )


async def complete_channel_delivery(
    db: AsyncSession,
    *,
    delivery_id: str,
    sent_count: int,
    external_message_ids: list[str],
    now: datetime,
) -> None:
    delivery = await db.get(ChannelDelivery, delivery_id)
    if delivery is None:
        return
    delivery.parts_sent += sent_count
    delivery.external_message_ids = [
        *delivery.external_message_ids,
        *external_message_ids,
    ]
    delivery.status = "succeeded"
    delivery.processed_at = now
    delivery.locked_at = None
    delivery.next_attempt_at = None
    delivery.last_error = None
    await db.flush()


async def fail_channel_delivery(
    db: AsyncSession,
    *,
    delivery_id: str,
    sent_count: int,
    external_message_ids: list[str],
    status: str,
    next_attempt_at: datetime | None,
    error: str,
) -> None:
    delivery = await db.get(ChannelDelivery, delivery_id)
    if delivery is None:
        return
    delivery.parts_sent += sent_count
    delivery.external_message_ids = [
        *delivery.external_message_ids,
        *external_message_ids,
    ]
    delivery.status = status
    delivery.next_attempt_at = next_attempt_at
    delivery.locked_at = None
    delivery.last_error = error[:1000]
    await db.flush()
