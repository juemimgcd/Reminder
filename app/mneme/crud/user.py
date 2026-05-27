from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.models.user import DEFAULT_USER_AVATAR_URL, User


async def create_user(
        db: AsyncSession,
        *,
        username: str,
        display_name: str | None = None,
        password_hash: str,
        avatar_url: str | None = None,
) -> User:
    user = User(
        username=username,
        display_name=display_name,
        password_hash=password_hash,
        avatar_url=avatar_url or DEFAULT_USER_AVATAR_URL,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    sql = select(User).where(User.id == user_id)
    res = await db.execute(sql)
    return res.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    sql = select(User).where(User.username == username)
    res = await db.execute(sql)
    return res.scalar_one_or_none()


async def list_users(db: AsyncSession) -> list[User]:
    sql = select(User).order_by(User.created_at.desc())
    res = await db.execute(sql)
    return list(res.scalars().all())
