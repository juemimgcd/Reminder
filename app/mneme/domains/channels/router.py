from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.channels.contracts import (
    ChannelConversationData,
    ChannelConversationUpdateRequest,
    ChannelDeliveryData,
    ChannelGatewayConfigurationData,
    ChannelGatewayError,
    ChannelIdentityData,
    ChannelLinkCodeCreateRequest,
    ChannelWebhookReceipt,
)
from app.mneme.channels.inbound import (
    accept_inbound_message,
    configure_channel_conversation,
    create_link_code,
)
from app.mneme.channels.registry import get_channel_adapter
from app.mneme.conf.config import settings
from app.mneme.conf.database import get_database, get_write_database
from app.mneme.crud.channel import (
    list_channel_conversations,
    list_channel_deliveries,
    list_channel_identities,
    retry_channel_delivery,
)
from app.mneme.models.user import User
from app.mneme.utils.auth import get_current_user
from app.mneme.utils.response import success_response

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("/configuration")
async def get_channel_configuration_api(
    _: User = Depends(get_current_user),
):
    app_id_configured = bool(settings.FEISHU_APP_ID.strip())
    app_secret_configured = bool(
        settings.FEISHU_APP_SECRET.get_secret_value().strip()
    )
    verification_token_configured = bool(
        settings.FEISHU_VERIFICATION_TOKEN.get_secret_value().strip()
    )
    return success_response(
        data=ChannelGatewayConfigurationData(
            channel="feishu",
            enabled=settings.FEISHU_ENABLED,
            ready=(
                settings.FEISHU_ENABLED
                and app_id_configured
                and app_secret_configured
                and verification_token_configured
            ),
            account_id=settings.FEISHU_ACCOUNT_ID,
            app_id_configured=app_id_configured,
            app_secret_configured=app_secret_configured,
            verification_token_configured=verification_token_configured,
            callback_path="/channels/feishu/webhook",
            delivery_queue=settings.CELERY_CHANNEL_QUEUE,
            max_text_chars=settings.FEISHU_MAX_TEXT_CHARS,
        )
    )


@router.post("/feishu/webhook")
async def feishu_webhook(request: Request):
    if not settings.FEISHU_ENABLED:
        raise HTTPException(status_code=503, detail="feishu channel is disabled")
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid webhook payload") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid webhook payload")
    adapter = get_channel_adapter("feishu")
    try:
        await adapter.verify_inbound(request, payload)
    except ChannelGatewayError as exc:
        raise HTTPException(status_code=401, detail="invalid channel callback") from exc
    challenge = payload.get("challenge")
    if isinstance(challenge, str):
        return JSONResponse({"challenge": challenge})
    messages = adapter.parse_inbound(payload)
    receipts = [
        await accept_inbound_message(message)
        for message in messages
    ]
    return ChannelWebhookReceipt(
        accepted=len(receipts),
        receipts=receipts,
    )


@router.post("/link-codes")
async def create_channel_link_code_api(
    payload: ChannelLinkCodeCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    if (
        payload.channel == "feishu"
        and settings.FEISHU_ACCOUNT_ID != "default"
        and payload.account_id != settings.FEISHU_ACCOUNT_ID
    ):
        raise HTTPException(
            status_code=400,
            detail="unknown feishu account_id",
        )
    data = await create_link_code(
        db,
        current_user=current_user,
        channel=payload.channel,
        account_id=payload.account_id,
    )
    return success_response(data=data, message="channel link code created")


@router.get("/identities")
async def list_channel_identities_api(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    identities = await list_channel_identities(
        db,
        mneme_user_id=current_user.id,
    )
    return success_response(
        data=[
            ChannelIdentityData(
                id=item.id,
                channel=item.channel,
                account_id=item.account_id,
                external_user_id=item.external_user_id,
                verified_at=item.verified_at,
                status=item.status,
            )
            for item in identities
        ]
    )


@router.get("/conversations")
async def list_channel_conversations_api(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    conversations = await list_channel_conversations(
        db,
        mneme_user_id=current_user.id,
    )
    return success_response(
        data=[_conversation_data(item) for item in conversations]
    )


@router.patch("/conversations/{conversation_id}")
async def configure_channel_conversation_api(
    conversation_id: str,
    payload: ChannelConversationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    conversation = await configure_channel_conversation(
        db,
        current_user=current_user,
        conversation_id=conversation_id,
        payload=payload,
    )
    return success_response(
        data=_conversation_data(conversation),
        message="channel conversation configured",
    )


@router.get("/deliveries")
async def list_channel_deliveries_api(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    deliveries = await list_channel_deliveries(
        db,
        mneme_user_id=current_user.id,
    )
    return success_response(
        data=[
            ChannelDeliveryData(
                id=item.id,
                channel=item.channel,
                agent_run_id=item.agent_run_id,
                assistant_message_id=item.assistant_message_id,
                status=item.status,
                parts_sent=item.parts_sent,
                part_count=len(item.parts_json),
                attempt_count=item.attempt_count,
                next_attempt_at=item.next_attempt_at,
                processed_at=item.processed_at,
                last_error=item.last_error,
            )
            for item in deliveries
        ]
    )


@router.post("/deliveries/{delivery_id}/retry")
async def retry_channel_delivery_api(
    delivery_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    delivery = await retry_channel_delivery(
        db,
        delivery_id=delivery_id,
        mneme_user_id=current_user.id,
    )
    if delivery is None:
        raise HTTPException(status_code=404, detail="channel delivery not found")
    return success_response(
        data=ChannelDeliveryData(
            id=delivery.id,
            channel=delivery.channel,
            agent_run_id=delivery.agent_run_id,
            assistant_message_id=delivery.assistant_message_id,
            status=delivery.status,
            parts_sent=delivery.parts_sent,
            part_count=len(delivery.parts_json),
            attempt_count=delivery.attempt_count,
            next_attempt_at=delivery.next_attempt_at,
            processed_at=delivery.processed_at,
            last_error=delivery.last_error,
        ),
        message=(
            "channel delivery already succeeded"
            if delivery.status == "succeeded"
            else "channel delivery queued for retry"
        ),
    )


def _conversation_data(item: Any) -> ChannelConversationData:
    return ChannelConversationData(
        id=item.id,
        channel=item.channel,
        account_id=item.account_id,
        external_conversation_id=item.external_conversation_id,
        external_thread_id=item.external_thread_id,
        chat_session_id=item.chat_session_id,
        knowledge_base_id=item.knowledge_base_id,
        answer_mode=item.answer_mode,
    )
