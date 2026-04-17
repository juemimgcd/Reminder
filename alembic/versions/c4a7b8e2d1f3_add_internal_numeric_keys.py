"""add internal numeric keys

Revision ID: c4a7b8e2d1f3
Revises: 5f6d0f6b7f4c
Create Date: 2026-04-06 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4a7b8e2d1f3"
down_revision: Union[str, Sequence[str], None] = "5f6d0f6b7f4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _get_inspector().get_table_names()


def _get_column_names(table_name: str) -> set[str]:
    return {item["name"] for item in _get_inspector().get_columns(table_name)}


def _get_index_names(table_name: str) -> set[str]:
    return {item["name"] for item in _get_inspector().get_indexes(table_name)}


def _get_unique_constraint_names(table_name: str) -> set[str]:
    return {item["name"] for item in _get_inspector().get_unique_constraints(table_name)}


def _get_foreign_key_names(table_name: str) -> set[str]:
    return {item["name"] for item in _get_inspector().get_foreign_keys(table_name)}


def _add_identity_bigint_column(table_name: str, column_name: str, comment: str) -> None:
    columns = _get_column_names(table_name)
    if column_name in columns:
        return

    # PostgreSQL rejects identity columns rendered as `... GENERATED ... IDENTITY NULL`.
    # Use NOT NULL here so Alembic emits valid DDL for existing tables.
    op.add_column(
        table_name,
        sa.Column(
            column_name,
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
            comment=comment,
        ),
    )
    op.execute(sa.text(f'UPDATE "{table_name}" SET "{column_name}" = DEFAULT WHERE "{column_name}" IS NULL'))
    op.alter_column(table_name, column_name, existing_type=sa.BigInteger(), nullable=False)


def _create_unique_constraint(table_name: str, name: str, columns: list[str]) -> None:
    unique_constraints = _get_unique_constraint_names(table_name)
    if name not in unique_constraints:
        op.create_unique_constraint(name, table_name, columns)


def _create_index(table_name: str, name: str, columns: list[str], *, unique: bool = False) -> None:
    indexes = _get_index_names(table_name)
    if name not in indexes:
        op.create_index(name, table_name, columns, unique=unique)


def _drop_index_if_exists(table_name: str, name: str) -> None:
    indexes = _get_index_names(table_name)
    if name in indexes:
        op.drop_index(name, table_name=table_name)


def _create_fk(
        table_name: str,
        name: str,
        local_cols: list[str],
        referent_table: str,
        remote_cols: list[str],
) -> None:
    foreign_keys = _get_foreign_key_names(table_name)
    if name not in foreign_keys:
        op.create_foreign_key(name, table_name, referent_table, local_cols, remote_cols)


def upgrade() -> None:
    if _has_table("knowledge_bases"):
        _add_identity_bigint_column("knowledge_bases", "pk", "内部主键")
        _create_unique_constraint("knowledge_bases", "uq_knowledge_bases_pk", ["pk"])
        _create_index("knowledge_bases", "idx_knowledge_bases_user_created_at", ["user_id", "created_at"])
        _create_index("knowledge_bases", "idx_knowledge_bases_user_is_default", ["user_id", "is_default"])

    if _has_table("documents"):
        _add_identity_bigint_column("documents", "pk", "内部主键")
        _create_unique_constraint("documents", "uq_documents_pk", ["pk"])

        document_columns = _get_column_names("documents")
        if "knowledge_base_pk" not in document_columns:
            op.add_column(
                "documents",
                sa.Column("knowledge_base_pk", sa.BigInteger(), nullable=True, comment="所属知识库内部主键"),
            )

        op.execute(
            sa.text(
                """
                UPDATE documents AS d
                SET knowledge_base_pk = kb.pk
                FROM knowledge_bases AS kb
                WHERE d.knowledge_base_id = kb.id
                  AND d.knowledge_base_pk IS NULL
                """
            )
        )
        op.alter_column("documents", "knowledge_base_pk", existing_type=sa.BigInteger(), nullable=False)

        _create_fk(
            "documents",
            "fk_documents_knowledge_base_pk_knowledge_bases",
            ["knowledge_base_pk"],
            "knowledge_bases",
            ["pk"],
        )
        _create_index("documents", "idx_documents_knowledge_base_pk", ["knowledge_base_pk"])
        _create_index("documents", "idx_documents_user_created_at", ["user_id", "created_at"])
        _create_index(
            "documents",
            "idx_documents_knowledge_base_pk_created_at",
            ["knowledge_base_pk", "created_at"],
        )
        _drop_index_if_exists("documents", "idx_documents_knowledge_base_id")

    if _has_table("chunks"):
        _add_identity_bigint_column("chunks", "pk", "内部主键")
        _create_unique_constraint("chunks", "uq_chunks_pk", ["pk"])

        chunk_columns = _get_column_names("chunks")
        if "document_pk" not in chunk_columns:
            op.add_column(
                "chunks",
                sa.Column("document_pk", sa.BigInteger(), nullable=True, comment="所属文档内部主键"),
            )

        op.execute(
            sa.text(
                """
                UPDATE chunks AS c
                SET document_pk = d.pk
                FROM documents AS d
                WHERE c.document_id = d.id
                  AND c.document_pk IS NULL
                """
            )
        )
        op.alter_column("chunks", "document_pk", existing_type=sa.BigInteger(), nullable=False)

        _create_fk("chunks", "fk_chunks_document_pk_documents", ["document_pk"], "documents", ["pk"])
        _create_index("chunks", "idx_chunks_document_pk", ["document_pk"])
        _create_index("chunks", "idx_chunks_document_pk_chunk_index", ["document_pk", "chunk_index"])
        _drop_index_if_exists("chunks", "idx_chunks_document_id")

    if _has_table("chat_sessions"):
        chat_columns = _get_column_names("chat_sessions")
        if "knowledge_base_pk" not in chat_columns:
            op.add_column(
                "chat_sessions",
                sa.Column("knowledge_base_pk", sa.BigInteger(), nullable=True, comment="所属知识库内部主键"),
            )

        op.execute(
            sa.text(
                """
                UPDATE chat_sessions AS cs
                SET knowledge_base_pk = kb.pk
                FROM knowledge_bases AS kb
                WHERE cs.knowledge_base_id = kb.id
                  AND cs.knowledge_base_pk IS NULL
                """
            )
        )
        op.alter_column("chat_sessions", "knowledge_base_pk", existing_type=sa.BigInteger(), nullable=False)

        _create_fk(
            "chat_sessions",
            "fk_chat_sessions_knowledge_base_pk_knowledge_bases",
            ["knowledge_base_pk"],
            "knowledge_bases",
            ["pk"],
        )
        _create_index("chat_sessions", "idx_chat_sessions_knowledge_base_pk", ["knowledge_base_pk"])
        _drop_index_if_exists("chat_sessions", "idx_chat_sessions_knowledge_base_id")

    if _has_table("memory_entries"):
        memory_columns = _get_column_names("memory_entries")

        if "knowledge_base_pk" not in memory_columns:
            op.add_column(
                "memory_entries",
                sa.Column("knowledge_base_pk", sa.BigInteger(), nullable=True, comment="所属知识库内部主键"),
            )

        if "document_pk" not in memory_columns:
            op.add_column(
                "memory_entries",
                sa.Column("document_pk", sa.BigInteger(), nullable=True, comment="所属文档内部主键"),
            )

        op.execute(
            sa.text(
                """
                UPDATE memory_entries AS me
                SET knowledge_base_pk = kb.pk
                FROM knowledge_bases AS kb
                WHERE me.knowledge_base_id = kb.id
                  AND me.knowledge_base_pk IS NULL
                """
            )
        )
        op.execute(
            sa.text(
                """
                UPDATE memory_entries AS me
                SET document_pk = d.pk
                FROM documents AS d
                WHERE me.document_id = d.id
                  AND me.document_pk IS NULL
                """
            )
        )
        op.alter_column("memory_entries", "knowledge_base_pk", existing_type=sa.BigInteger(), nullable=False)
        op.alter_column("memory_entries", "document_pk", existing_type=sa.BigInteger(), nullable=False)

        _create_fk(
            "memory_entries",
            "fk_memory_entries_knowledge_base_pk_knowledge_bases",
            ["knowledge_base_pk"],
            "knowledge_bases",
            ["pk"],
        )
        _create_fk(
            "memory_entries",
            "fk_memory_entries_document_pk_documents",
            ["document_pk"],
            "documents",
            ["pk"],
        )
        _create_index("memory_entries", "idx_memory_entries_knowledge_base_pk", ["knowledge_base_pk"])
        _create_index("memory_entries", "idx_memory_entries_document_pk", ["document_pk"])
        _drop_index_if_exists("memory_entries", "idx_memory_entries_knowledge_base_id")
        _drop_index_if_exists("memory_entries", "idx_memory_entries_document_id")


def downgrade() -> None:
    if _has_table("memory_entries"):
        memory_fks = _get_foreign_key_names("memory_entries")
        if "fk_memory_entries_document_pk_documents" in memory_fks:
            op.drop_constraint("fk_memory_entries_document_pk_documents", "memory_entries", type_="foreignkey")
        if "fk_memory_entries_knowledge_base_pk_knowledge_bases" in memory_fks:
            op.drop_constraint("fk_memory_entries_knowledge_base_pk_knowledge_bases", "memory_entries", type_="foreignkey")

        _drop_index_if_exists("memory_entries", "idx_memory_entries_document_pk")
        _drop_index_if_exists("memory_entries", "idx_memory_entries_knowledge_base_pk")
        _create_index("memory_entries", "idx_memory_entries_knowledge_base_id", ["knowledge_base_id"])
        _create_index("memory_entries", "idx_memory_entries_document_id", ["document_id"])

        memory_columns = _get_column_names("memory_entries")
        if "document_pk" in memory_columns:
            op.drop_column("memory_entries", "document_pk")
        if "knowledge_base_pk" in memory_columns:
            op.drop_column("memory_entries", "knowledge_base_pk")

    if _has_table("chat_sessions"):
        chat_fks = _get_foreign_key_names("chat_sessions")
        if "fk_chat_sessions_knowledge_base_pk_knowledge_bases" in chat_fks:
            op.drop_constraint("fk_chat_sessions_knowledge_base_pk_knowledge_bases", "chat_sessions", type_="foreignkey")

        _drop_index_if_exists("chat_sessions", "idx_chat_sessions_knowledge_base_pk")
        _create_index("chat_sessions", "idx_chat_sessions_knowledge_base_id", ["knowledge_base_id"])

        chat_columns = _get_column_names("chat_sessions")
        if "knowledge_base_pk" in chat_columns:
            op.drop_column("chat_sessions", "knowledge_base_pk")

    if _has_table("chunks"):
        chunk_fks = _get_foreign_key_names("chunks")
        if "fk_chunks_document_pk_documents" in chunk_fks:
            op.drop_constraint("fk_chunks_document_pk_documents", "chunks", type_="foreignkey")

        _drop_index_if_exists("chunks", "idx_chunks_document_pk_chunk_index")
        _drop_index_if_exists("chunks", "idx_chunks_document_pk")
        _create_index("chunks", "idx_chunks_document_id", ["document_id"])

        chunk_uniques = _get_unique_constraint_names("chunks")
        if "uq_chunks_pk" in chunk_uniques:
            op.drop_constraint("uq_chunks_pk", "chunks", type_="unique")

        chunk_columns = _get_column_names("chunks")
        if "document_pk" in chunk_columns:
            op.drop_column("chunks", "document_pk")
        if "pk" in chunk_columns:
            op.drop_column("chunks", "pk")

    if _has_table("documents"):
        document_fks = _get_foreign_key_names("documents")
        if "fk_documents_knowledge_base_pk_knowledge_bases" in document_fks:
            op.drop_constraint("fk_documents_knowledge_base_pk_knowledge_bases", "documents", type_="foreignkey")

        _drop_index_if_exists("documents", "idx_documents_knowledge_base_pk_created_at")
        _drop_index_if_exists("documents", "idx_documents_user_created_at")
        _drop_index_if_exists("documents", "idx_documents_knowledge_base_pk")
        _create_index("documents", "idx_documents_knowledge_base_id", ["knowledge_base_id"])

        document_uniques = _get_unique_constraint_names("documents")
        if "uq_documents_pk" in document_uniques:
            op.drop_constraint("uq_documents_pk", "documents", type_="unique")

        document_columns = _get_column_names("documents")
        if "knowledge_base_pk" in document_columns:
            op.drop_column("documents", "knowledge_base_pk")
        if "pk" in document_columns:
            op.drop_column("documents", "pk")

    if _has_table("knowledge_bases"):
        _drop_index_if_exists("knowledge_bases", "idx_knowledge_bases_user_is_default")
        _drop_index_if_exists("knowledge_bases", "idx_knowledge_bases_user_created_at")

        kb_uniques = _get_unique_constraint_names("knowledge_bases")
        if "uq_knowledge_bases_pk" in kb_uniques:
            op.drop_constraint("uq_knowledge_bases_pk", "knowledge_bases", type_="unique")

        kb_columns = _get_column_names("knowledge_bases")
        if "pk" in kb_columns:
            op.drop_column("knowledge_bases", "pk")
