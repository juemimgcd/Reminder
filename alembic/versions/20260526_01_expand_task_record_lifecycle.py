"""expand task record lifecycle

Revision ID: 20260526_01
Revises: 20260514_01
Create Date: 2026-05-26 13:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260526_01"
down_revision: Union[str, Sequence[str], None] = "20260514_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_inspector():
    return sa.inspect(op.get_bind())


def _get_column_names(table_name: str) -> set[str]:
    return {item["name"] for item in _get_inspector().get_columns(table_name)}


def _get_index_names(table_name: str) -> set[str]:
    return {item["name"] for item in _get_inspector().get_indexes(table_name)}


def upgrade() -> None:
    columns = _get_column_names("task_records")
    if "progress_stage" not in columns:
        op.add_column("task_records", sa.Column("progress_stage", sa.String(length=100), nullable=True, comment="当前执行阶段"))
    if "queue_name" not in columns:
        op.add_column("task_records", sa.Column("queue_name", sa.String(length=100), nullable=True, comment="消息队列名称"))
    if "celery_task_id" not in columns:
        op.add_column("task_records", sa.Column("celery_task_id", sa.String(length=100), nullable=True, comment="Celery 任务ID"))
    if "attempt_count" not in columns:
        op.add_column(
            "task_records",
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0", comment="已尝试次数"),
        )
    if "max_attempts" not in columns:
        op.add_column(
            "task_records",
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3", comment="最大尝试次数"),
        )
    if "result_summary" not in columns:
        op.add_column("task_records", sa.Column("result_summary", sa.Text(), nullable=True, comment="任务结果摘要"))

    op.execute(
        sa.text(
            """
            UPDATE task_records
            SET progress_stage = status,
                status = 'running'
            WHERE status IN ('parsing', 'chunking', 'memory_extracting', 'embedding', 'vector_upserting')
            """
        )
    )
    op.execute(sa.text("UPDATE task_records SET status = 'pending' WHERE status = 'queued'"))
    op.execute(sa.text("UPDATE task_records SET status = 'succeeded' WHERE status = 'completed'"))
    op.execute(sa.text("UPDATE task_records SET status = 'cancelled' WHERE status = 'canceled'"))
    op.execute(sa.text("UPDATE task_records SET celery_task_id = id WHERE celery_task_id IS NULL"))

    indexes = _get_index_names("task_records")
    if "idx_task_records_type_status" not in indexes:
        op.create_index("idx_task_records_type_status", "task_records", ["task_type", "status"], unique=False)


def downgrade() -> None:
    indexes = _get_index_names("task_records")
    if "idx_task_records_type_status" in indexes:
        op.drop_index("idx_task_records_type_status", table_name="task_records")

    op.execute(sa.text("UPDATE task_records SET status = 'queued' WHERE status = 'pending'"))
    op.execute(sa.text("UPDATE task_records SET status = 'completed' WHERE status = 'succeeded'"))
    op.execute(sa.text("UPDATE task_records SET status = 'canceled' WHERE status = 'cancelled'"))
    op.execute(
        sa.text(
            """
            UPDATE task_records
            SET status = progress_stage
            WHERE status = 'running'
              AND progress_stage IN ('parsing', 'chunking', 'memory_extracting', 'embedding', 'vector_upserting')
            """
        )
    )

    columns = _get_column_names("task_records")
    if "result_summary" in columns:
        op.drop_column("task_records", "result_summary")
    if "max_attempts" in columns:
        op.drop_column("task_records", "max_attempts")
    if "attempt_count" in columns:
        op.drop_column("task_records", "attempt_count")
    if "celery_task_id" in columns:
        op.drop_column("task_records", "celery_task_id")
    if "queue_name" in columns:
        op.drop_column("task_records", "queue_name")
    if "progress_stage" in columns:
        op.drop_column("task_records", "progress_stage")
