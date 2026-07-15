"""add immutable outbox enqueue time

Revision ID: 20260715_03
Revises: 20260715_02
"""

import sqlalchemy as sa

from alembic import op

revision = "20260715_03"
down_revision = "20260715_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("outbox_events", sa.Column("enqueued_at", sa.DateTime(timezone=True)))
    # Legacy rows did not retain a creation timestamp. next_attempt_at is the best available
    # enqueue approximation, followed by lock/process time and finally this migration time.
    op.execute(
        "UPDATE outbox_events SET enqueued_at = "
        "COALESCE(next_attempt_at, locked_at, processed_at, CURRENT_TIMESTAMP)"
    )
    op.alter_column(
        "outbox_events",
        "enqueued_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    op.execute(
        """
        CREATE FUNCTION reject_outbox_enqueued_at_update() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF NEW.enqueued_at IS DISTINCT FROM OLD.enqueued_at THEN
            RAISE EXCEPTION 'outbox enqueued_at is immutable';
          END IF;
          RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_outbox_enqueued_at_immutable
        BEFORE UPDATE OF enqueued_at ON outbox_events
        FOR EACH ROW EXECUTE FUNCTION reject_outbox_enqueued_at_update();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_outbox_enqueued_at_immutable ON outbox_events")
    op.execute("DROP FUNCTION IF EXISTS reject_outbox_enqueued_at_update()")
    op.drop_column("outbox_events", "enqueued_at")
