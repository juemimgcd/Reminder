from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.models.chat_message import ChatMessage


async def create_chat_message(
    db: AsyncSession,
    *,
    message_id: str,
    session_id: str,
    user_id: int,
    knowledge_base_id: str | None,
    knowledge_base_pk: int | None,
    role: str,
    content: str,
    sources_json: list | None = None,
    citations_json: list | None = None,
    route_json: dict | None = None,
    model_config_id: str | None = None,
    agent_run_id: str | None = None,
    answer_metadata_json: dict | None = None,
) -> ChatMessage:
    message = ChatMessage(
        id=message_id,
        session_id=session_id,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        knowledge_base_pk=knowledge_base_pk,
        role=role,
        content=content,
        sources_json=sources_json,
        citations_json=citations_json,
        route_json=route_json,
        model_config_id=model_config_id,
        agent_run_id=agent_run_id,
        answer_metadata_json=answer_metadata_json,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    return message


async def list_chat_messages(
    db: AsyncSession,
    *,
    session_id: str,
    user_id: int,
) -> list[ChatMessage]:
    sql = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id, ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
    )
    result = await db.execute(sql)
    return list(result.scalars().all())


async def delete_chat_messages(
    db: AsyncSession,
    *,
    session_id: str,
    user_id: int,
) -> int:
    sql = delete(ChatMessage).where(ChatMessage.session_id == session_id, ChatMessage.user_id == user_id)
    result = await db.execute(sql)
    return result.rowcount or 0
