import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.knowledge_base import KnowledgeBase


async def create_knowledge_base(
        db: AsyncSession,
        *,
        knowledge_base_id: str,
        user_id: int,
        name: str,
        description: str | None = None,
        is_default: bool = False,
) -> KnowledgeBase:
    knowledge_base = KnowledgeBase(
        id=knowledge_base_id,
        user_id=user_id,
        name=name,
        description=description,
        is_default=is_default,
    )
    db.add(knowledge_base)
    await db.flush()
    await db.refresh(knowledge_base)
    return knowledge_base


async def get_knowledge_base_by_id(
        db: AsyncSession,
        knowledge_base_id: str,
) -> KnowledgeBase | None:
    sql = select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id)
    res = await db.execute(sql)
    return res.scalar_one_or_none()


async def list_knowledge_bases_by_user_id(
        db: AsyncSession,
        *,
        user_id: int,
) -> list[KnowledgeBase]:
    sql = (
        select(KnowledgeBase)
        .where(KnowledgeBase.user_id == user_id)
        .order_by(KnowledgeBase.created_at.asc())
    )
    res = await db.execute(sql)
    return list(res.scalars().all())


async def get_default_knowledge_base_by_user_id(
        db: AsyncSession,
        *,
        user_id: int,
) -> KnowledgeBase | None:
    sql = (
        select(KnowledgeBase)
        .where(KnowledgeBase.user_id == user_id)
        .where(KnowledgeBase.is_default.is_(True))
    )
    res = await db.execute(sql)
    return res.scalar_one_or_none()


async def get_or_create_default_knowledge_base(
        db: AsyncSession,
        *,
        user_id: int,
) -> KnowledgeBase:
    knowledge_base = await get_default_knowledge_base_by_user_id(
        db,
        user_id=user_id,
    )
    if knowledge_base:
        return knowledge_base

    return await create_knowledge_base(
        db,
        knowledge_base_id=f"kb_{uuid.uuid4().hex[:12]}",
        user_id=user_id,
        name="默认个人知识库",
        description="系统自动创建的默认知识库",
        is_default=True,
    )


async def delete_knowledge_base_by_id(
        db: AsyncSession,
        *,
        knowledge_base_id: str,
) -> int:
    sql = delete(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id)
    res = await db.execute(sql)
    return res.rowcount or 0














