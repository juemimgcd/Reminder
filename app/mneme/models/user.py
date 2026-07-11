from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.models.base import Base


DEFAULT_USER_AVATAR_URL = "/static/avatars/default.png"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_username", "username", unique=True),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
        comment="user id",
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False, comment="username")
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="display name")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="password hash")
    avatar_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default=DEFAULT_USER_AVATAR_URL,
        comment="avatar URL",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="last login time",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"
