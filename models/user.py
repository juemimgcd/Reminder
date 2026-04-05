from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


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
        comment="用户ID",
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False, comment="用户名")
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="展示名称")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    avatar_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default=DEFAULT_USER_AVATAR_URL,
        comment="头像地址",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最近登录时间",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"
