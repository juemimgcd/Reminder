"""add ai model configs

Revision ID: 20260707_02
Revises: 20260707_01
Create Date: 2026-07-07 19:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260707_02"
down_revision: Union[str, Sequence[str], None] = "20260707_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _get_inspector().get_table_names()


def upgrade() -> None:
    if _has_table("ai_model_configs"):
        return

    op.create_table(
        "ai_model_configs",
        sa.Column("id", sa.String(length=64), nullable=False, comment="model config id"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="owner user id"),
        sa.Column("label", sa.String(length=120), nullable=False, comment="display label"),
        sa.Column("provider", sa.String(length=64), nullable=False, comment="provider key"),
        sa.Column("base_url", sa.String(length=500), nullable=False, comment="OpenAI-compatible base URL"),
        sa.Column("model_name", sa.String(length=255), nullable=False, comment="model name"),
        sa.Column("api_key_ciphertext", sa.Text(), nullable=True, comment="encrypted API key"),
        sa.Column("temperature", sa.Float(), server_default="0", nullable=False),
        sa.Column("context_window", sa.Integer(), server_default="64000", nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ai_model_configs_user_id", "ai_model_configs", ["user_id"])
    op.create_index("idx_ai_model_configs_user_default", "ai_model_configs", ["user_id", "is_default"])


def downgrade() -> None:
    if not _has_table("ai_model_configs"):
        return

    op.drop_index("idx_ai_model_configs_user_default", table_name="ai_model_configs")
    op.drop_index("idx_ai_model_configs_user_id", table_name="ai_model_configs")
    op.drop_table("ai_model_configs")
