from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.clients.memory_agent_client import MemoryAgentClient
from app.mneme.conf.config import settings
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id
from app.mneme.domains.tasks.outbox import enqueue_user_memory_settings_changed
from app.mneme.models.chat_message import ChatMessage
from app.mneme.models.chat_session import ChatSession
from app.mneme.models.chunk import Chunk
from app.mneme.models.document import Document
from app.mneme.models.user import User
from app.mneme.schemas.memory_agent import (
    CanonicalMemoryData,
    ConversationMemorySettingsData,
    GovernedMemoryPage,
    MemoryCandidateData,
    MemoryCandidatePage,
    MemoryConfirmationAction,
    MemoryConfirmationData,
)
from app.mneme.utils.exceptions import BusinessException

TOKEN_ALGORITHM = "HS256"
TOKEN_ISSUER = "mneme-backend"
ACTION_AUDIENCE = "mneme-memory-action"
PURGE_AUDIENCE = "memory-agent-purge"
CURSOR_AUDIENCE = "mneme-memory-cursor"
TOKEN_TTL = timedelta(minutes=5)
CURSOR_TTL = timedelta(hours=1)


async def require_owned_knowledge_base(db: AsyncSession, *, current_user: User, knowledge_base_id: str | None) -> None:
    if knowledge_base_id is None:
        return
    knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id)
    if knowledge_base is None or knowledge_base.user_id != current_user.id:
        raise BusinessException(message="knowledge base not found", code=4042, status_code=404)


async def require_owned_source(
    db: AsyncSession,
    *,
    current_user: User,
    source_id: str,
    knowledge_base_id: str | None,
) -> None:
    document_scope = await db.scalar(
        select(Document.knowledge_base_id)
        .outerjoin(Chunk, Chunk.document_pk == Document.pk)
        .where(
            Document.user_id == current_user.id,
            or_(Document.id == source_id, Chunk.id == source_id),
        )
        .limit(1)
    )
    if document_scope is not None:
        if document_scope != knowledge_base_id:
            raise BusinessException(message="source scope mismatch", code=4007, status_code=403)
        return
    conversation_scope = await db.scalar(
        select(ChatSession.knowledge_base_id)
        .outerjoin(ChatMessage, ChatMessage.session_id == ChatSession.id)
        .where(
            ChatSession.user_id == current_user.id,
            or_(ChatSession.id == source_id, ChatMessage.id == source_id),
        )
        .limit(1)
    )
    if conversation_scope != knowledge_base_id or conversation_scope is None and knowledge_base_id is not None:
        raise BusinessException(message="source not found", code=4044, status_code=404)
    if conversation_scope is None:
        exists = await db.scalar(
            select(ChatSession.id)
            .outerjoin(ChatMessage, ChatMessage.session_id == ChatSession.id)
            .where(
                ChatSession.user_id == current_user.id,
                or_(ChatSession.id == source_id, ChatMessage.id == source_id),
            )
            .limit(1)
        )
        if exists is None:
            raise BusinessException(message="source not found", code=4044, status_code=404)


def issue_confirmation(
    *, owner_id: int, knowledge_base_id: str | None, action: MemoryConfirmationAction, target_id: str
) -> MemoryConfirmationData:
    now = datetime.now(UTC)
    expires_at = now + TOKEN_TTL
    claims: dict[str, Any] = {
        "iss": TOKEN_ISSUER,
        "iat": now,
        "exp": expires_at,
        "jti": uuid4().hex,
        "owner_id": owner_id,
        "knowledge_base_id": knowledge_base_id,
    }
    if action.startswith("purge_"):
        selector_type = {
            "purge_source": "source_id",
            "purge_knowledge_base": "knowledge_base_id",
            "purge_account": "owner_id",
        }[action]
        selector_value: str | int = owner_id if action == "purge_account" else target_id
        claims.update(
            aud=PURGE_AUDIENCE,
            purpose="memory-purge",
            selector_type=selector_type,
            selector_value=selector_value,
        )
    else:
        claims.update(aud=ACTION_AUDIENCE, purpose="memory-action", action=action, target_id=target_id)
    token = jwt.encode(claims, _secret(), algorithm=TOKEN_ALGORITHM)
    return MemoryConfirmationData(action=action, target_id=target_id, expires_at=expires_at, confirmation_token=token)


def verify_confirmation(
    token: str,
    *,
    owner_id: int,
    knowledge_base_id: str | None,
    action: MemoryConfirmationAction,
    target_id: str,
) -> None:
    audience = PURGE_AUDIENCE if action.startswith("purge_") else ACTION_AUDIENCE
    try:
        claims = jwt.decode(
            token,
            _secret(),
            algorithms=[TOKEN_ALGORITHM],
            audience=audience,
            issuer=TOKEN_ISSUER,
            options={"require": ["iss", "aud", "iat", "exp", "jti", "purpose", "owner_id", "knowledge_base_id"]},
        )
    except jwt.PyJWTError:
        raise BusinessException(message="confirmation invalid or expired", code=4036, status_code=403) from None
    valid = claims.get("owner_id") == owner_id and claims.get("knowledge_base_id") == knowledge_base_id
    if action.startswith("purge_"):
        selector_type = {
            "purge_source": "source_id",
            "purge_knowledge_base": "knowledge_base_id",
            "purge_account": "owner_id",
        }[action]
        selector_value: str | int = owner_id if action == "purge_account" else target_id
        valid = (
            valid
            and claims.get("purpose") == "memory-purge"
            and claims.get("selector_type") == selector_type
            and claims.get("selector_value") == selector_value
        )
    else:
        valid = (
            valid
            and claims.get("purpose") == "memory-action"
            and claims.get("action") == action
            and claims.get("target_id") == target_id
        )
    if not valid:
        raise BusinessException(message="confirmation scope mismatch", code=4036, status_code=403)


def decode_cursor(
    cursor: str | None,
    *,
    resource: str,
    limit: int,
    owner_id: int,
    knowledge_base_id: str | None,
    filters: dict[str, Any],
) -> int:
    if cursor is None:
        return 0
    try:
        claims = jwt.decode(
            cursor, _secret(), algorithms=[TOKEN_ALGORITHM], audience=CURSOR_AUDIENCE, issuer=TOKEN_ISSUER
        )
    except jwt.PyJWTError:
        raise BusinessException(message="invalid memory cursor", code=4008, status_code=400) from None
    offset = claims.get("offset")
    if (
        claims.get("owner_id") != owner_id
        or claims.get("knowledge_base_id") != knowledge_base_id
        or claims.get("resource") != resource
        or claims.get("limit") != limit
        or claims.get("filters") != filters
        or not isinstance(offset, int)
        or isinstance(offset, bool)
        or not 0 <= offset <= 1_000_000
    ):
        raise BusinessException(message="memory cursor scope mismatch", code=4008, status_code=400)
    return offset


def encode_cursor(
    *,
    resource: str,
    limit: int,
    offset: int,
    owner_id: int,
    knowledge_base_id: str | None,
    filters: dict[str, Any],
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "iss": TOKEN_ISSUER,
            "aud": CURSOR_AUDIENCE,
            "iat": now,
            "exp": now + CURSOR_TTL,
            "owner_id": owner_id,
            "knowledge_base_id": knowledge_base_id,
            "resource": resource,
            "limit": limit,
            "filters": filters,
            "offset": offset,
        },
        _secret(),
        algorithm=TOKEN_ALGORITHM,
    )


async def list_memories(
    *, owner_id: int, knowledge_base_id: str | None, filters: dict[str, Any], cursor: str | None, limit: int
) -> GovernedMemoryPage:
    offset = decode_cursor(
        cursor,
        resource="memories",
        limit=limit,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        filters=filters,
    )
    async with MemoryAgentClient() as client:
        payload = await client.list_memories(
            owner_id=owner_id, knowledge_base_id=knowledge_base_id, params={**filters, "offset": offset, "limit": limit}
        )
    items = [CanonicalMemoryData.model_validate(item) for item in payload.get("items", [])]
    next_cursor = (
        encode_cursor(
            resource="memories",
            limit=limit,
            offset=offset + len(items),
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            filters=filters,
        )
        if len(items) == limit
        else None
    )
    return GovernedMemoryPage(items=items, next_cursor=next_cursor, total=int(payload.get("total", len(items))))


async def list_candidates(
    *, owner_id: int, knowledge_base_id: str | None, filters: dict[str, Any], cursor: str | None, limit: int
) -> MemoryCandidatePage:
    offset = decode_cursor(
        cursor,
        resource="candidates",
        limit=limit,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        filters=filters,
    )
    async with MemoryAgentClient() as client:
        payload = await client.list_candidates(
            owner_id=owner_id, knowledge_base_id=knowledge_base_id, params={**filters, "offset": offset, "limit": limit}
        )
    items = [MemoryCandidateData.model_validate(item) for item in payload.get("items", [])]
    next_cursor = (
        encode_cursor(
            resource="candidates",
            limit=limit,
            offset=offset + len(items),
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            filters=filters,
        )
        if len(items) == limit
        else None
    )
    total = int(payload.get("total", len(items)))
    return MemoryCandidatePage(items=items, next_cursor=next_cursor, total=total, pending_count=total)


async def update_settings(db: AsyncSession, *, owner_id: int, enabled: bool) -> ConversationMemorySettingsData:
    await enqueue_user_memory_settings_changed(
        db, owner_id=owner_id, automatic_conversation_memory=enabled, occurred_at=datetime.now(UTC)
    )
    return ConversationMemorySettingsData(automatic_conversation_memory=enabled, applied=False)


def _secret() -> str:
    value = settings.MEMORY_AGENT_SERVICE_JWT_SECRET.get_secret_value()
    if not value:
        raise BusinessException(message="memory agent credentials are not configured", code=5032, status_code=503)
    return value
