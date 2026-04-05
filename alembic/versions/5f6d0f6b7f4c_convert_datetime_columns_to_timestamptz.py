"""convert datetime columns to timestamptz

Revision ID: 5f6d0f6b7f4c
Revises: a1c9f0b4d2e7
Create Date: 2026-04-05 16:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5f6d0f6b7f4c"
down_revision: Union[str, Sequence[str], None] = "a1c9f0b4d2e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_COLUMNS: dict[str, list[str]] = {
    "users": ["created_at", "updated_at", "last_login_at"],
    "knowledge_bases": ["created_at", "updated_at"],
    "documents": ["created_at", "updated_at"],
    "chat_sessions": ["created_at", "updated_at"],
    "memory_entries": ["created_at", "updated_at"],
    "chunks": ["created_at", "updated_at"],
    "task_records": ["created_at", "updated_at"],
}


def _get_inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _get_inspector().get_table_names()


def _get_column_names(table_name: str) -> set[str]:
    return {item["name"] for item in _get_inspector().get_columns(table_name)}


def _alter_datetime_column(
        *,
        table_name: str,
        column_name: str,
        nullable: bool,
        timezone_enabled: bool,
) -> None:
    current_type = sa.DateTime(timezone=not timezone_enabled)
    target_type = sa.DateTime(timezone=timezone_enabled)
    using_expr = f"{column_name} AT TIME ZONE 'UTC'"

    kwargs = {
        "existing_type": current_type,
        "type_": target_type,
        "existing_nullable": nullable,
        "postgresql_using": using_expr,
    }

    if column_name in {"created_at", "updated_at"}:
        kwargs["existing_server_default"] = sa.text("now()")

    op.alter_column(
        table_name,
        column_name,
        **kwargs,
    )


def upgrade() -> None:
    for table_name, columns in TABLE_COLUMNS.items():
        if not _has_table(table_name):
            continue

        existing_columns = _get_column_names(table_name)
        for column_name in columns:
            if column_name not in existing_columns:
                continue
            _alter_datetime_column(
                table_name=table_name,
                column_name=column_name,
                nullable=(column_name == "last_login_at"),
                timezone_enabled=True,
            )


def downgrade() -> None:
    for table_name, columns in TABLE_COLUMNS.items():
        if not _has_table(table_name):
            continue

        existing_columns = _get_column_names(table_name)
        for column_name in columns:
            if column_name not in existing_columns:
                continue
            _alter_datetime_column(
                table_name=table_name,
                column_name=column_name,
                nullable=(column_name == "last_login_at"),
                timezone_enabled=False,
            )
