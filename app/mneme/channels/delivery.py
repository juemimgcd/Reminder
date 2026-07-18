import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.channels.contracts import (
    ChannelDeliveryRequest,
    ChannelGatewayError,
    ChannelPartialDeliveryError,
    OutboundPart,
    PersistedAnswer,
)
from app.mneme.channels.registry import get_channel_adapter
from app.mneme.conf.config import settings
from app.mneme.conf.database import open_read_session, open_write_session
from app.mneme.crud.channel import (
    claim_channel_delivery,
    complete_channel_delivery,
    create_or_get_channel_delivery,
    fail_channel_delivery,
    get_channel_inbound_by_run_id,
    list_dispatchable_channel_deliveries,
    recover_stale_channel_deliveries,
)
from app.mneme.models.channel import ChannelDelivery, ChannelInboundMessage
from app.mneme.models.chat_message import ChatMessage


async def enqueue_channel_notice(
    db: AsyncSession,
    *,
    inbound: ChannelInboundMessage,
    content: str,
    notice_kind: str,
    mneme_user_id: int | None,
) -> ChannelDelivery:
    delivery, _ = await create_or_get_channel_delivery(
        db,
        values={
            "id": f"delivery_{uuid.uuid4().hex}",
            "idempotency_key": f"channel-notice:{inbound.id}:{notice_kind}",
            "channel": inbound.channel,
            "account_id": inbound.account_id,
            "external_conversation_id": inbound.external_conversation_id,
            "external_thread_id": inbound.external_thread_id,
            "reply_to_external_message_id": inbound.external_message_id,
            "mneme_user_id": mneme_user_id,
            "inbound_message_id": inbound.id,
            "parts_json": [
                OutboundPart(kind="text", content=content).model_dump(mode="json")
            ],
            "max_attempts": settings.CHANNEL_DELIVERY_MAX_ATTEMPTS,
        },
    )
    return delivery


async def enqueue_answer_channel_delivery(
    db: AsyncSession,
    *,
    agent_run_id: str,
    assistant_message: ChatMessage,
) -> ChannelDelivery | None:
    inbound = await get_channel_inbound_by_run_id(
        db,
        agent_run_id=agent_run_id,
    )
    if inbound is None:
        return None
    adapter = get_channel_adapter(inbound.channel)
    parts = adapter.render_answer(
        PersistedAnswer(
            message_id=assistant_message.id,
            run_id=agent_run_id,
            content=assistant_message.content,
            citations=assistant_message.citations_json or [],
        )
    )
    if not parts:
        return None
    delivery, _ = await create_or_get_channel_delivery(
        db,
        values={
            "id": f"delivery_{uuid.uuid4().hex}",
            "idempotency_key": (
                f"channel-answer:{inbound.id}:{assistant_message.id}"
            ),
            "channel": inbound.channel,
            "account_id": inbound.account_id,
            "external_conversation_id": inbound.external_conversation_id,
            "external_thread_id": inbound.external_thread_id,
            "reply_to_external_message_id": inbound.external_message_id,
            "mneme_user_id": assistant_message.user_id,
            "inbound_message_id": inbound.id,
            "agent_run_id": agent_run_id,
            "assistant_message_id": assistant_message.id,
            "parts_json": [part.model_dump(mode="json") for part in parts],
            "max_attempts": settings.CHANNEL_DELIVERY_MAX_ATTEMPTS,
        },
    )
    return delivery


async def process_channel_delivery(delivery_id: str) -> dict[str, int | str | bool]:
    now = datetime.now(timezone.utc)
    async with open_write_session() as db:
        delivery = await claim_channel_delivery(
            db,
            delivery_id=delivery_id,
            now=now,
        )
    if delivery is None:
        return {"delivery_id": delivery_id, "skipped": True}

    remaining = [
        OutboundPart.model_validate(part)
        for part in delivery.parts_json[delivery.parts_sent :]
    ]
    request = ChannelDeliveryRequest(
        delivery_id=delivery.id,
        account_id=delivery.account_id,
        conversation_id=delivery.external_conversation_id,
        thread_id=delivery.external_thread_id,
        reply_to_message_id=delivery.reply_to_external_message_id,
        parts=remaining,
    )
    try:
        result = await get_channel_adapter(delivery.channel).send(request)
    except ChannelPartialDeliveryError as exc:
        await _mark_delivery_failure(
            delivery,
            sent_count=exc.sent_count,
            external_message_ids=exc.external_message_ids,
            retryable=exc.retryable,
            error=str(exc),
        )
        raise
    except ChannelGatewayError as exc:
        await _mark_delivery_failure(
            delivery,
            sent_count=0,
            external_message_ids=[],
            retryable=exc.retryable,
            error=str(exc),
        )
        raise
    except Exception as exc:
        await _mark_delivery_failure(
            delivery,
            sent_count=0,
            external_message_ids=[],
            retryable=True,
            error="channel delivery failed",
        )
        raise ChannelGatewayError(
            "channel delivery failed",
            retryable=True,
        ) from exc

    async with open_write_session() as db:
        await complete_channel_delivery(
            db,
            delivery_id=delivery.id,
            sent_count=result.sent_count,
            external_message_ids=result.external_message_ids,
            now=datetime.now(timezone.utc),
        )
    return {
        "delivery_id": delivery.id,
        "status": "succeeded",
        "sent_count": result.sent_count,
        "skipped": False,
    }


async def dispatch_channel_deliveries(
    *,
    limit: int | None = None,
) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    async with open_write_session() as db:
        recovered = await recover_stale_channel_deliveries(
            db,
            stale_before=now
            - timedelta(seconds=settings.CHANNEL_DELIVERY_STALE_SECONDS),
            now=now,
        )
    async with open_read_session() as db:
        deliveries = await list_dispatchable_channel_deliveries(
            db,
            now=now,
            limit=limit or settings.CHANNEL_DELIVERY_DISPATCH_BATCH_SIZE,
        )
    dispatched = 0
    failed = 0
    for delivery in deliveries:
        try:
            await process_channel_delivery(delivery.id)
            dispatched += 1
        except Exception:
            failed += 1
    return {
        "matched": len(deliveries),
        "dispatched": dispatched,
        "failed": failed,
        "recovered": recovered,
    }


async def _mark_delivery_failure(
    delivery: ChannelDelivery,
    *,
    sent_count: int,
    external_message_ids: list[str],
    retryable: bool,
    error: str,
) -> None:
    exhausted = delivery.attempt_count >= delivery.max_attempts
    status = "failed" if retryable and not exhausted else "dead_letter"
    next_attempt_at = None
    if status == "failed":
        delay = settings.CHANNEL_DELIVERY_RETRY_BASE_SECONDS * (
            2 ** max(0, delivery.attempt_count - 1)
        )
        next_attempt_at = datetime.now(timezone.utc) + timedelta(
            seconds=min(delay, 3600)
        )
    async with open_write_session() as db:
        await fail_channel_delivery(
            db,
            delivery_id=delivery.id,
            sent_count=sent_count,
            external_message_ids=external_message_ids,
            status=status,
            next_attempt_at=next_attempt_at,
            error=error,
        )
