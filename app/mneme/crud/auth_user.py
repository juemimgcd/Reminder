from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.crud.user import get_user_by_id
from app.mneme.models.user import DEFAULT_USER_AVATAR_URL, User


def ensure_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def create_user_account(
        db: AsyncSession,
        *,
        username: str,
        display_name: str | None,
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


async def update_user_last_login_at(
        db: AsyncSession,
        *,
        user_id: int,
        login_at: datetime | None = None,
) -> User | None:
    user = await get_user_by_id(db, user_id=user_id)
    if not user:
        return None

    current_login_at = login_at or datetime.now(UTC)
    user.last_login_at = ensure_utc_datetime(current_login_at)

    await db.flush()
    await db.refresh(user)
    return user
