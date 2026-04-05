"""add auth fields to users

Revision ID: a1c9f0b4d2e7
Revises: 561e0b8d63ef
Create Date: 2026-04-05 12:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1c9f0b4d2e7"
down_revision: Union[str, Sequence[str], None] = "561e0b8d63ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_inspector():
    return sa.inspect(op.get_bind())


def _get_column_names(table_name: str) -> set[str]:
    return {item["name"] for item in _get_inspector().get_columns(table_name)}


def _get_index_names(table_name: str) -> set[str]:
    return {item["name"] for item in _get_inspector().get_indexes(table_name)}


def upgrade() -> None:
    user_columns = _get_column_names("users")

    if "password_hash" not in user_columns:
        op.add_column(
            "users",
            sa.Column("password_hash", sa.String(length=255), nullable=True, comment="密码哈希"),
        )

    if "avatar_url" not in user_columns:
        op.add_column(
            "users",
            sa.Column(
                "avatar_url",
                sa.String(length=500),
                nullable=False,
                server_default=sa.text("'/static/avatars/default.png'"),
                comment="头像地址",
            ),
        )

    if "last_login_at" not in user_columns:
        op.add_column(
            "users",
            sa.Column("last_login_at", sa.DateTime(), nullable=True, comment="最近登录时间"),
        )

    op.execute(
        sa.text(
            "UPDATE users SET password_hash = '__SET_PASSWORD__' WHERE password_hash IS NULL"
        )
    )
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=False)

    user_indexes = _get_index_names("users")
    if "idx_users_is_active" in user_indexes:
        op.drop_index("idx_users_is_active", table_name="users")

    if "is_active" in user_columns:
        op.drop_column("users", "is_active")


def downgrade() -> None:
    user_indexes = _get_index_names("users")

    user_columns = _get_column_names("users")
    if "last_login_at" in user_columns:
        op.drop_column("users", "last_login_at")
    if "avatar_url" in user_columns:
        op.drop_column("users", "avatar_url")
    if "password_hash" in user_columns:
        op.drop_column("users", "password_hash")
