"""add user scope and knowledge bases

Revision ID: 561e0b8d63ef
Revises: d44ce83b855d
Create Date: 2026-04-05 11:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "561e0b8d63ef"
down_revision: Union[str, Sequence[str], None] = "d44ce83b855d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_USER_ID = 1
DEFAULT_KNOWLEDGE_BASE_ID = "kb_system_default"


def _get_inspector():
    return sa.inspect(op.get_bind())


def _get_table_names() -> set[str]:
    return set(_get_inspector().get_table_names())


def _get_column_names(table_name: str) -> set[str]:
    return {item["name"] for item in _get_inspector().get_columns(table_name)}


def _get_index_names(table_name: str) -> set[str]:
    return {item["name"] for item in _get_inspector().get_indexes(table_name)}


def _get_fk_names(table_name: str) -> set[str]:
    return {
        item["name"]
        for item in _get_inspector().get_foreign_keys(table_name)
        if item.get("name")
    }


def upgrade() -> None:
    if "users" not in _get_table_names():
        op.create_table(
            "users",
            sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False, comment="用户ID"),
            sa.Column("username", sa.String(length=100), nullable=False, comment="用户名"),
            sa.Column("display_name", sa.String(length=255), nullable=True, comment="展示名称"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_users_username", "users", ["username"], unique=True)

    if "knowledge_bases" not in _get_table_names():
        op.create_table(
            "knowledge_bases",
            sa.Column("id", sa.String(length=64), nullable=False, comment="知识库ID"),
            sa.Column("user_id", sa.BigInteger(), nullable=False, comment="所属用户ID"),
            sa.Column("name", sa.String(length=255), nullable=False, comment="知识库名称"),
            sa.Column("description", sa.Text(), nullable=True, comment="知识库描述"),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否默认知识库"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_knowledge_bases_user_id", "knowledge_bases", ["user_id"], unique=False)
        op.create_index("idx_knowledge_bases_is_default", "knowledge_bases", ["is_default"], unique=False)

    op.execute(
        sa.text(
            """
            INSERT INTO users (id, username, display_name)
            VALUES (:user_id, :username, :display_name)
            ON CONFLICT (id) DO NOTHING
            """
        ).bindparams(
            user_id=DEFAULT_USER_ID,
            username="system_default",
            display_name="系统默认用户",
        )
    )
    op.execute(sa.text("SELECT setval(pg_get_serial_sequence('users', 'id'), GREATEST((SELECT COALESCE(MAX(id), 1) FROM users), 1))"))
    op.execute(
        sa.text(
            """
            INSERT INTO knowledge_bases (id, user_id, name, description, is_default)
            VALUES (:kb_id, :user_id, :name, :description, true)
            ON CONFLICT (id) DO NOTHING
            """
        ).bindparams(
            kb_id=DEFAULT_KNOWLEDGE_BASE_ID,
            user_id=DEFAULT_USER_ID,
            name="默认个人知识库",
            description="为历史数据回填的默认知识库",
        )
    )

    document_columns = _get_column_names("documents")
    if "user_id" not in document_columns:
        op.add_column(
            "documents",
            sa.Column("user_id", sa.BigInteger(), nullable=True, comment="所属用户ID"),
        )

    op.execute(
        sa.text(
            "UPDATE documents SET user_id = :user_id WHERE user_id IS NULL"
        ).bindparams(user_id=DEFAULT_USER_ID)
    )
    op.execute(
        sa.text(
            "UPDATE documents SET knowledge_base_id = :kb_id WHERE knowledge_base_id IS NULL"
        ).bindparams(kb_id=DEFAULT_KNOWLEDGE_BASE_ID)
    )
    op.alter_column("documents", "user_id", existing_type=sa.BigInteger(), nullable=False)
    op.alter_column("documents", "knowledge_base_id", existing_type=sa.String(length=64), nullable=False)

    document_fks = _get_fk_names("documents")
    if "fk_documents_user_id_users" not in document_fks:
        op.create_foreign_key(
            "fk_documents_user_id_users",
            "documents",
            "users",
            ["user_id"],
            ["id"],
        )
    if "fk_documents_knowledge_base_id_knowledge_bases" not in document_fks:
        op.create_foreign_key(
            "fk_documents_knowledge_base_id_knowledge_bases",
            "documents",
            "knowledge_bases",
            ["knowledge_base_id"],
            ["id"],
        )

    document_indexes = _get_index_names("documents")
    if "idx_documents_user_id" not in document_indexes:
        op.create_index("idx_documents_user_id", "documents", ["user_id"], unique=False)

    chat_columns = _get_column_names("chat_sessions")
    if "user_id" not in chat_columns:
        op.add_column(
            "chat_sessions",
            sa.Column("user_id", sa.BigInteger(), nullable=True, comment="所属用户ID"),
        )

    op.execute(
        sa.text(
            "UPDATE chat_sessions SET user_id = :user_id WHERE user_id IS NULL"
        ).bindparams(user_id=DEFAULT_USER_ID)
    )
    op.execute(
        sa.text(
            "UPDATE chat_sessions SET knowledge_base_id = :kb_id WHERE knowledge_base_id IS NULL"
        ).bindparams(kb_id=DEFAULT_KNOWLEDGE_BASE_ID)
    )
    op.alter_column("chat_sessions", "user_id", existing_type=sa.BigInteger(), nullable=False)
    op.alter_column("chat_sessions", "knowledge_base_id", existing_type=sa.String(length=64), nullable=False)

    chat_fks = _get_fk_names("chat_sessions")
    if "fk_chat_sessions_user_id_users" not in chat_fks:
        op.create_foreign_key(
            "fk_chat_sessions_user_id_users",
            "chat_sessions",
            "users",
            ["user_id"],
            ["id"],
        )
    if "fk_chat_sessions_knowledge_base_id_knowledge_bases" not in chat_fks:
        op.create_foreign_key(
            "fk_chat_sessions_knowledge_base_id_knowledge_bases",
            "chat_sessions",
            "knowledge_bases",
            ["knowledge_base_id"],
            ["id"],
        )

    chat_indexes = _get_index_names("chat_sessions")
    if "idx_chat_sessions_user_id" not in chat_indexes:
        op.create_index("idx_chat_sessions_user_id", "chat_sessions", ["user_id"], unique=False)

    if "memory_entries" not in _get_table_names():
        op.create_table(
            "memory_entries",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("knowledge_base_id", sa.String(length=64), nullable=False),
            sa.Column("document_id", sa.String(length=64), nullable=False),
            sa.Column("chunk_id", sa.String(length=64), nullable=False),
            sa.Column("entry_name", sa.String(length=255), nullable=False),
            sa.Column("entry_type", sa.String(length=50), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("evidence_text", sa.Text(), nullable=False),
            sa.Column("importance_score", sa.Float(), nullable=False, server_default=sa.text("0.5")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
            sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_memory_entries_user_id", "memory_entries", ["user_id"], unique=False)
        op.create_index("idx_memory_entries_knowledge_base_id", "memory_entries", ["knowledge_base_id"], unique=False)
        op.create_index("idx_memory_entries_document_id", "memory_entries", ["document_id"], unique=False)
        op.create_index("idx_memory_entries_entry_type", "memory_entries", ["entry_type"], unique=False)
        op.create_index("idx_memory_entries_chunk_id", "memory_entries", ["chunk_id"], unique=False)
    else:
        memory_columns = _get_column_names("memory_entries")
        if "user_id" not in memory_columns:
            op.add_column(
                "memory_entries",
                sa.Column("user_id", sa.BigInteger(), nullable=True),
            )
        if "knowledge_base_id" not in memory_columns:
            op.add_column(
                "memory_entries",
                sa.Column("knowledge_base_id", sa.String(length=64), nullable=True),
            )

        op.execute(
            sa.text(
                """
                UPDATE memory_entries AS me
                SET user_id = d.user_id,
                    knowledge_base_id = d.knowledge_base_id
                FROM documents AS d
                WHERE me.document_id = d.id
                  AND (me.user_id IS NULL OR me.knowledge_base_id IS NULL)
                """
            )
        )
        op.execute(
            sa.text(
                "UPDATE memory_entries SET user_id = :user_id WHERE user_id IS NULL"
            ).bindparams(user_id=DEFAULT_USER_ID)
        )
        op.execute(
            sa.text(
                "UPDATE memory_entries SET knowledge_base_id = :kb_id WHERE knowledge_base_id IS NULL"
            ).bindparams(kb_id=DEFAULT_KNOWLEDGE_BASE_ID)
        )

        op.alter_column("memory_entries", "user_id", existing_type=sa.BigInteger(), nullable=False)
        op.alter_column("memory_entries", "knowledge_base_id", existing_type=sa.String(length=64), nullable=False)

        memory_fks = _get_fk_names("memory_entries")
        if "fk_memory_entries_user_id_users" not in memory_fks:
            op.create_foreign_key(
                "fk_memory_entries_user_id_users",
                "memory_entries",
                "users",
                ["user_id"],
                ["id"],
            )
        if "fk_memory_entries_knowledge_base_id_knowledge_bases" not in memory_fks:
            op.create_foreign_key(
                "fk_memory_entries_knowledge_base_id_knowledge_bases",
                "memory_entries",
                "knowledge_bases",
                ["knowledge_base_id"],
                ["id"],
            )

        memory_indexes = _get_index_names("memory_entries")
        if "idx_memory_entries_user_id" not in memory_indexes:
            op.create_index("idx_memory_entries_user_id", "memory_entries", ["user_id"], unique=False)
        if "idx_memory_entries_knowledge_base_id" not in memory_indexes:
            op.create_index("idx_memory_entries_knowledge_base_id", "memory_entries", ["knowledge_base_id"], unique=False)


def downgrade() -> None:
    if "memory_entries" in _get_table_names():
        memory_indexes = _get_index_names("memory_entries")
        if "idx_memory_entries_knowledge_base_id" in memory_indexes:
            op.drop_index("idx_memory_entries_knowledge_base_id", table_name="memory_entries")
        if "idx_memory_entries_user_id" in memory_indexes:
            op.drop_index("idx_memory_entries_user_id", table_name="memory_entries")

        memory_fks = _get_fk_names("memory_entries")
        if "fk_memory_entries_knowledge_base_id_knowledge_bases" in memory_fks:
            op.drop_constraint("fk_memory_entries_knowledge_base_id_knowledge_bases", "memory_entries", type_="foreignkey")
        if "fk_memory_entries_user_id_users" in memory_fks:
            op.drop_constraint("fk_memory_entries_user_id_users", "memory_entries", type_="foreignkey")

        memory_columns = _get_column_names("memory_entries")
        if "knowledge_base_id" in memory_columns:
            op.drop_column("memory_entries", "knowledge_base_id")
        if "user_id" in memory_columns:
            op.drop_column("memory_entries", "user_id")

    if "chat_sessions" in _get_table_names():
        chat_indexes = _get_index_names("chat_sessions")
        if "idx_chat_sessions_user_id" in chat_indexes:
            op.drop_index("idx_chat_sessions_user_id", table_name="chat_sessions")

        chat_fks = _get_fk_names("chat_sessions")
        if "fk_chat_sessions_knowledge_base_id_knowledge_bases" in chat_fks:
            op.drop_constraint("fk_chat_sessions_knowledge_base_id_knowledge_bases", "chat_sessions", type_="foreignkey")
        if "fk_chat_sessions_user_id_users" in chat_fks:
            op.drop_constraint("fk_chat_sessions_user_id_users", "chat_sessions", type_="foreignkey")

        chat_columns = _get_column_names("chat_sessions")
        if "knowledge_base_id" in chat_columns:
            op.alter_column("chat_sessions", "knowledge_base_id", existing_type=sa.String(length=64), nullable=True)
        if "user_id" in chat_columns:
            op.drop_column("chat_sessions", "user_id")

    if "documents" in _get_table_names():
        document_indexes = _get_index_names("documents")
        if "idx_documents_user_id" in document_indexes:
            op.drop_index("idx_documents_user_id", table_name="documents")

        document_fks = _get_fk_names("documents")
        if "fk_documents_knowledge_base_id_knowledge_bases" in document_fks:
            op.drop_constraint("fk_documents_knowledge_base_id_knowledge_bases", "documents", type_="foreignkey")
        if "fk_documents_user_id_users" in document_fks:
            op.drop_constraint("fk_documents_user_id_users", "documents", type_="foreignkey")

        document_columns = _get_column_names("documents")
        if "knowledge_base_id" in document_columns:
            op.alter_column("documents", "knowledge_base_id", existing_type=sa.String(length=64), nullable=True)
        if "user_id" in document_columns:
            op.drop_column("documents", "user_id")

    if "knowledge_bases" in _get_table_names():
        knowledge_base_indexes = _get_index_names("knowledge_bases")
        if "idx_knowledge_bases_is_default" in knowledge_base_indexes:
            op.drop_index("idx_knowledge_bases_is_default", table_name="knowledge_bases")
        if "idx_knowledge_bases_user_id" in knowledge_base_indexes:
            op.drop_index("idx_knowledge_bases_user_id", table_name="knowledge_bases")
        op.drop_table("knowledge_bases")

    if "users" in _get_table_names():
        user_indexes = _get_index_names("users")
        if "idx_users_username" in user_indexes:
            op.drop_index("idx_users_username", table_name="users")
        op.drop_table("users")
