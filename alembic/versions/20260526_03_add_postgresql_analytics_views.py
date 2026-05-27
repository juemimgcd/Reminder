"""add postgresql analytics views

Revision ID: 20260526_03
Revises: 20260526_02
Create Date: 2026-05-26 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260526_03"
down_revision: Union[str, Sequence[str], None] = "20260526_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE VIEW mneme_kb_document_analytics AS
            WITH document_stats AS (
                SELECT
                    d.knowledge_base_pk,
                    COUNT(*) AS document_count,
                    COALESCE(SUM(d.file_size), 0) AS total_file_size
                FROM documents d
                GROUP BY d.knowledge_base_pk
            ),
            chunk_stats AS (
                SELECT
                    d.knowledge_base_pk,
                    COUNT(c.pk) AS chunk_count,
                    COUNT(DISTINCT c.section_id) FILTER (WHERE c.section_id IS NOT NULL) AS section_count
                FROM documents d
                LEFT JOIN chunks c ON c.document_pk = d.pk
                GROUP BY d.knowledge_base_pk
            ),
            memory_stats AS (
                SELECT
                    me.knowledge_base_pk,
                    COUNT(me.id) AS memory_entry_count
                FROM memory_entries me
                GROUP BY me.knowledge_base_pk
            )
            SELECT
                kb.id AS knowledge_base_id,
                kb.user_id AS user_id,
                COALESCE(ds.document_count, 0) AS document_count,
                COALESCE(ds.total_file_size, 0) AS total_file_size,
                COALESCE(cs.chunk_count, 0) AS chunk_count,
                COALESCE(cs.section_count, 0) AS section_count,
                COALESCE(ms.memory_entry_count, 0) AS memory_entry_count
            FROM knowledge_bases kb
            LEFT JOIN document_stats ds ON ds.knowledge_base_pk = kb.pk
            LEFT JOIN chunk_stats cs ON cs.knowledge_base_pk = kb.pk
            LEFT JOIN memory_stats ms ON ms.knowledge_base_pk = kb.pk
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE VIEW mneme_document_status_analytics AS
            SELECT
                d.knowledge_base_id AS knowledge_base_id,
                d.user_id AS user_id,
                d.status AS status,
                COUNT(*) AS count
            FROM documents d
            GROUP BY d.knowledge_base_id, d.user_id, d.status
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE VIEW mneme_task_status_analytics AS
            SELECT
                d.knowledge_base_id AS knowledge_base_id,
                d.user_id AS user_id,
                tr.task_type AS task_type,
                tr.status AS status,
                COUNT(*) AS count
            FROM task_records tr
            JOIN documents d ON d.id = tr.target_id
            GROUP BY d.knowledge_base_id, d.user_id, tr.task_type, tr.status
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE VIEW mneme_outbox_status_analytics AS
            SELECT
                d.knowledge_base_id AS knowledge_base_id,
                d.user_id AS user_id,
                oe.target_backend AS target_backend,
                oe.status AS status,
                COUNT(*) AS count
            FROM outbox_events oe
            JOIN documents d ON d.id = oe.aggregate_id
            WHERE oe.aggregate_type = 'document'
            GROUP BY d.knowledge_base_id, d.user_id, oe.target_backend, oe.status
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP VIEW IF EXISTS mneme_outbox_status_analytics"))
    op.execute(sa.text("DROP VIEW IF EXISTS mneme_task_status_analytics"))
    op.execute(sa.text("DROP VIEW IF EXISTS mneme_document_status_analytics"))
    op.execute(sa.text("DROP VIEW IF EXISTS mneme_kb_document_analytics"))
