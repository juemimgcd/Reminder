import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.channels.contracts import (
    ChannelConversationUpdateRequest,
    ChannelInboundReceipt,
    ChannelLinkCodeData,
    NormalizedInboundMessage,
)
from app.mneme.channels.delivery import enqueue_channel_notice
from app.mneme.conf.config import settings
from app.mneme.conf.database import open_write_session
from app.mneme.crud.channel import (
    consume_channel_link_code,
    create_channel_conversation,
    create_channel_identity,
    create_channel_link_code,
    create_or_get_channel_inbound,
    get_channel_conversation,
    get_channel_conversation_by_scope,
    get_channel_identity,
)
from app.mneme.crud.chat_session import (
    create_chat_session,
    get_chat_session_by_id,
)
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id
from app.mneme.memoria.run_models import AgentRunRecord
from app.mneme.memoria.run_submission import submit_agent_run
from app.mneme.models.channel import ChannelConversation
from app.mneme.models.user import User
from app.mneme.utils.exceptions import BusinessException

_BIND_COMMAND = re.compile(
    r"^\s*(?:/mneme\s+bind|/bind|绑定)\s+([A-Z0-9]{8})\s*$",
    re.IGNORECASE,
)


async def create_link_code(
    db: AsyncSession,
    *,
    current_user: User,
    channel: str,
    account_id: str,
) -> ChannelLinkCodeData:
    code = secrets.token_hex(4).upper()
    expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=settings.CHANNEL_LINK_CODE_TTL_SECONDS
    )
    await create_channel_link_code(
        db,
        link_id=f"link_{uuid.uuid4().hex}",
        channel=channel,
        account_id=account_id,
        mneme_user_id=current_user.id,
        code_hash=_link_code_hash(code),
        expires_at=expires_at,
    )
    return ChannelLinkCodeData(
        channel=channel,
        account_id=account_id,
        code=code,
        expires_at=expires_at,
        binding_command=f"/mneme bind {code}",
    )


async def process_inbound_message(
    message: NormalizedInboundMessage,
) -> ChannelInboundReceipt:
    async with open_write_session() as db:
        inbound, created = await create_or_get_channel_inbound(
            db,
            values=_inbound_values(message),
        )
        if not created and inbound.status != "received":
            return ChannelInboundReceipt(
                message_id=message.message_id,
                status="duplicate",
                run_id=inbound.agent_run_id,
                code=inbound.rejection_code,
            )

        binding = _BIND_COMMAND.match(message.text)
        if binding:
            return await _bind_external_identity(
                db,
                inbound=inbound,
                message=message,
                code=binding.group(1).upper(),
            )

        identity = await get_channel_identity(
            db,
            channel=message.channel,
            account_id=message.account_id,
            external_user_id=message.sender_id,
        )
        if identity is None or identity.status != "active":
            inbound.status = "rejected"
            inbound.rejection_code = "CHANNEL_IDENTITY_REQUIRED"
            await enqueue_channel_notice(
                db,
                inbound=inbound,
                content=(
                    "This external account is not linked to Mneme. "
                    "Generate a link code in the Mneme web app, then send "
                    "`/mneme bind CODE` here."
                ),
                notice_kind="identity_required",
                mneme_user_id=None,
            )
            return ChannelInboundReceipt(
                message_id=message.message_id,
                status="rejected",
                code=inbound.rejection_code,
            )

        conversation = await _ensure_channel_conversation(
            db,
            message=message,
            mneme_user_id=identity.mneme_user_id,
        )
        if conversation.mneme_user_id != identity.mneme_user_id:
            inbound.status = "rejected"
            inbound.rejection_code = "CHANNEL_CONVERSATION_OWNER_CONFLICT"
            await enqueue_channel_notice(
                db,
                inbound=inbound,
                content=(
                    "This channel conversation is already linked to another "
                    "Mneme owner and cannot be used for private retrieval."
                ),
                notice_kind="owner_conflict",
                mneme_user_id=identity.mneme_user_id,
            )
            return ChannelInboundReceipt(
                message_id=message.message_id,
                status="rejected",
                code=inbound.rejection_code,
            )
        inbound.identity_id = identity.id
        inbound.channel_conversation_id = conversation.id

        if not message.text.strip() or (
            message.attachments and message.text.lstrip().startswith("[")
        ):
            inbound.status = "rejected"
            inbound.rejection_code = "CHANNEL_ATTACHMENT_UNSUPPORTED"
            await enqueue_channel_notice(
                db,
                inbound=inbound,
                content=(
                    "This attachment type is not ingested from Feishu yet. "
                    "Upload it in the Mneme web app, then ask about it here."
                ),
                notice_kind="attachment_unsupported",
                mneme_user_id=identity.mneme_user_id,
            )
            return ChannelInboundReceipt(
                message_id=message.message_id,
                status="rejected",
                code=inbound.rejection_code,
            )

        run_id = inbound.agent_run_id or f"run_{uuid.uuid4().hex}"
        inbound.agent_run_id = run_id
        inbound.status = "submitted"
        await db.commit()

        record = AgentRunRecord.create(
            run_id=run_id,
            session_id=conversation.chat_session_id,
            user_id=identity.mneme_user_id,
            client_request_id=f"channel:{_inbound_key(message)}",
            question=message.text,
            top_k=4,
            answer_mode=conversation.answer_mode,
            max_attempts=settings.AGENT_RUN_MAX_ATTEMPTS,
        )
        record, _ = await submit_agent_run(db, record)
        return ChannelInboundReceipt(
            message_id=message.message_id,
            status="submitted" if created else "duplicate",
            run_id=record.run_id,
        )


async def accept_inbound_message(
    message: NormalizedInboundMessage,
) -> ChannelInboundReceipt:
    async with open_write_session() as db:
        inbound, created = await create_or_get_channel_inbound(
            db,
            values=_inbound_values(message),
        )
        status = inbound.status
        run_id = inbound.agent_run_id
        rejection_code = inbound.rejection_code
    if status == "received":
        from app.mneme.channels.tasks import process_channel_inbound_task

        process_channel_inbound_task.apply_async(
            kwargs={"message_payload": message.model_dump(mode="json")}
        )
    return ChannelInboundReceipt(
        message_id=message.message_id,
        status="accepted" if created else "duplicate",
        run_id=run_id,
        code=rejection_code,
    )


async def configure_channel_conversation(
    db: AsyncSession,
    *,
    current_user: User,
    conversation_id: str,
    payload: ChannelConversationUpdateRequest,
) -> ChannelConversation:
    conversation = await get_channel_conversation(
        db,
        conversation_id=conversation_id,
        mneme_user_id=current_user.id,
    )
    if conversation is None:
        raise BusinessException(
            message="channel conversation not found",
            code=4601,
            status_code=404,
        )
    current_session = await get_chat_session_by_id(
        db,
        session_id=conversation.chat_session_id,
        user_id=current_user.id,
    )
    if current_session is None:
        raise BusinessException(
            message="mapped chat session not found",
            code=4602,
            status_code=404,
        )
    session = current_session
    if (
        payload.chat_session_id is not None
        and payload.chat_session_id != current_session.id
    ):
        target_session = await get_chat_session_by_id(
            db,
            session_id=payload.chat_session_id,
            user_id=current_user.id,
        )
        if target_session is None:
            raise BusinessException(
                message="target chat session does not belong to current user",
                code=4606,
                status_code=403,
            )
        session = target_session
    knowledge_base = None
    if payload.answer_mode != "general_chat":
        if payload.knowledge_base_id is None:
            raise BusinessException(
                message="knowledge base is required for private channel modes",
                code=4603,
                status_code=400,
            )
        knowledge_base = await get_knowledge_base_by_id(
            db,
            payload.knowledge_base_id,
        )
        if knowledge_base is None or knowledge_base.user_id != current_user.id:
            raise BusinessException(
                message="knowledge base does not belong to current user",
                code=4604,
                status_code=403,
            )
    target_knowledge_base_id = knowledge_base.id if knowledge_base else None
    if (
        session.message_count > 0
        and (
            session.knowledge_base_id != target_knowledge_base_id
            or session.answer_mode != payload.answer_mode
        )
    ):
        raise BusinessException(
            message=(
                "channel mapping must preserve the scope of a chat session "
                "that already has messages"
            ),
            code=4605,
            status_code=409,
        )
    conversation.chat_session_id = session.id
    conversation.knowledge_base_id = target_knowledge_base_id
    conversation.answer_mode = payload.answer_mode
    session.knowledge_base_id = target_knowledge_base_id
    session.knowledge_base_pk = knowledge_base.pk if knowledge_base else None
    session.answer_mode = payload.answer_mode
    await db.flush()
    return conversation


async def _bind_external_identity(
    db: AsyncSession,
    *,
    inbound,
    message: NormalizedInboundMessage,
    code: str,
) -> ChannelInboundReceipt:
    now = datetime.now(timezone.utc)
    link = await consume_channel_link_code(
        db,
        code_hash=_link_code_hash(code),
        channel=message.channel,
        account_id=message.account_id,
        external_user_id=message.sender_id,
        now=now,
    )
    if link is None:
        inbound.status = "rejected"
        inbound.rejection_code = "CHANNEL_LINK_CODE_INVALID"
        await enqueue_channel_notice(
            db,
            inbound=inbound,
            content="The Mneme link code is invalid or expired.",
            notice_kind="invalid_link_code",
            mneme_user_id=None,
        )
        return ChannelInboundReceipt(
            message_id=message.message_id,
            status="rejected",
            code=inbound.rejection_code,
        )

    identity = await get_channel_identity(
        db,
        channel=message.channel,
        account_id=message.account_id,
        external_user_id=message.sender_id,
    )
    if identity is not None and identity.mneme_user_id != link.mneme_user_id:
        inbound.status = "rejected"
        inbound.rejection_code = "CHANNEL_IDENTITY_ALREADY_BOUND"
        await enqueue_channel_notice(
            db,
            inbound=inbound,
            content="This external account is already linked to another Mneme user.",
            notice_kind="identity_already_bound",
            mneme_user_id=None,
        )
        return ChannelInboundReceipt(
            message_id=message.message_id,
            status="rejected",
            code=inbound.rejection_code,
        )
    if identity is None:
        identity = await create_channel_identity(
            db,
            identity_id=f"identity_{uuid.uuid4().hex}",
            channel=message.channel,
            account_id=message.account_id,
            external_user_id=message.sender_id,
            mneme_user_id=link.mneme_user_id,
            verified_at=now,
            metadata={"binding": "short_code"},
        )
    conversation = await _ensure_channel_conversation(
        db,
        message=message,
        mneme_user_id=identity.mneme_user_id,
    )
    inbound.identity_id = identity.id
    inbound.channel_conversation_id = conversation.id
    inbound.status = "bound"
    await enqueue_channel_notice(
        db,
        inbound=inbound,
        content=(
            "Feishu is now linked to Mneme. The conversation starts in "
            "General chat mode; configure a private knowledge-base scope in "
            "the Mneme web app before using private retrieval."
        ),
        notice_kind="identity_bound",
        mneme_user_id=identity.mneme_user_id,
    )
    return ChannelInboundReceipt(
        message_id=message.message_id,
        status="bound",
    )


async def _ensure_channel_conversation(
    db: AsyncSession,
    *,
    message: NormalizedInboundMessage,
    mneme_user_id: int,
) -> ChannelConversation:
    scope_key = _conversation_scope_key(message)
    lock_key = int(scope_key[:15], 16)
    await db.execute(select(func.pg_advisory_xact_lock(lock_key)))
    conversation = await get_channel_conversation_by_scope(
        db,
        scope_key=scope_key,
    )
    if conversation is not None:
        return conversation
    session_id = f"chat_{uuid.uuid4().hex}"
    await create_chat_session(
        db,
        session_id=session_id,
        user_id=mneme_user_id,
        knowledge_base_id=None,
        knowledge_base_pk=None,
        title=f"{message.channel.title()} conversation",
        answer_mode="general_chat",
    )
    return await create_channel_conversation(
        db,
        conversation_id=f"channel_conversation_{uuid.uuid4().hex}",
        scope_key=scope_key,
        channel=message.channel,
        account_id=message.account_id,
        external_conversation_id=message.conversation_id,
        external_thread_id=message.thread_id,
        mneme_user_id=mneme_user_id,
        chat_session_id=session_id,
    )


def _link_code_hash(code: str) -> str:
    return hashlib.sha256(
        f"{settings.JWT_SECRET}:{code.upper()}".encode()
    ).hexdigest()


def _inbound_key(message: NormalizedInboundMessage) -> str:
    return hashlib.sha256(
        f"{message.channel}\0{message.account_id}\0{message.message_id}".encode()
    ).hexdigest()


def _conversation_scope_key(message: NormalizedInboundMessage) -> str:
    return hashlib.sha256(
        (
            f"{message.channel}\0{message.account_id}\0"
            f"{message.conversation_id}\0{message.thread_id or ''}"
        ).encode()
    ).hexdigest()


def _payload_hash(message: NormalizedInboundMessage) -> str:
    return hashlib.sha256(
        message.model_dump_json().encode()
    ).hexdigest()


def _inbound_values(message: NormalizedInboundMessage) -> dict:
    return {
        "id": f"inbound_{uuid.uuid4().hex}",
        "idempotency_key": _inbound_key(message),
        "channel": message.channel,
        "account_id": message.account_id,
        "external_message_id": message.message_id,
        "external_sender_id": message.sender_id,
        "external_conversation_id": message.conversation_id,
        "external_thread_id": message.thread_id,
        "text": message.text,
        "attachments_json": [
            item.model_dump(mode="json") for item in message.attachments
        ],
        "payload_hash": _payload_hash(message),
        "status": "received",
    }
