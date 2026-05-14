"""add chunk section fields

Revision ID: 20260514_01
Revises: c4a7b8e2d1f3
Create Date: 2026-05-14 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260514_01"
down_revision: Union[str, Sequence[str], None] = "c4a7b8e2d1f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("section_id", sa.String(length=80), nullable=True))
    op.add_column("chunks", sa.Column("section_title", sa.String(length=255), nullable=True))
    op.add_column("chunks", sa.Column("section_level", sa.Integer(), nullable=True))
    op.add_column("chunks", sa.Column("section_path", sa.String(length=500), nullable=True))
    op.add_column("chunks", sa.Column("section_summary", sa.Text(), nullable=True))
    op.add_column("chunks", sa.Column("section_chunk_index", sa.Integer(), nullable=True))
    op.create_index(
        "idx_chunks_document_pk_section_id",
        "chunks",
        ["document_pk", "section_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_chunks_document_pk_section_id", table_name="chunks")
    op.drop_column("chunks", "section_chunk_index")
    op.drop_column("chunks", "section_summary")
    op.drop_column("chunks", "section_path")
    op.drop_column("chunks", "section_level")
    op.drop_column("chunks", "section_title")
    op.drop_column("chunks", "section_id")
