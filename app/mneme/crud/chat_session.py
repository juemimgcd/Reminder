from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.models.chat_session import ChatSession


async def create_chat_session(
    db: AsyncSession,
    *,
    session_id: str,
    user_id: int,
    knowledge_base_id: str | None,
    knowledge_base_pk: int | None,
    title: str | None,
    answer_mode: str = "kb_qa",
) -> ChatSession:
    session = ChatSession(
        id=session_id,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        knowledge_base_pk=knowledge_base_pk,
        title=title,
        answer_mode=answer_mode,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def get_chat_session_by_id(
    db: AsyncSession,
    *,
    session_id: str,
    user_id: int | None = None,
) -> ChatSession | None:
    sql = select(ChatSession).where(ChatSession.id == session_id)
    if user_id is not None:
        sql = sql.where(ChatSession.user_id == user_id)
    result = await db.execute(sql)
    return result.scalar_one_or_none()


async def list_chat_sessions(
    db: AsyncSession,
    *,
    user_id: int,
    knowledge_base_id: str | None = None,
    include_archived: bool = False,
) -> list[ChatSession]:
    sql = select(ChatSession).where(ChatSession.user_id == user_id)
    if knowledge_base_id:
        sql = sql.where(ChatSession.knowledge_base_id == knowledge_base_id)
    if not include_archived:
        sql = sql.where(ChatSession.archived_at.is_(None))
    sql = sql.order_by(ChatSession.last_message_at.desc().nullslast(), ChatSession.created_at.desc())
    result = await db.execute(sql)
    return list(result.scalars().all())


async def delete_chat_session(
    db: AsyncSession,
    *,
    session_id: str,
    user_id: int,
) -> int:
    sql = delete(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    result = await db.execute(sql)
    return result.rowcount or 0
