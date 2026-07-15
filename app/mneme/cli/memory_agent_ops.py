import argparse
import asyncio
import json
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.mneme.conf.database import engine, open_read_session
from app.mneme.models.outbox_event import OutboxEvent


async def _snapshot() -> dict[str, int | float]:
    async with open_read_session() as db:
        row = (
            await db.execute(
                select(
                    func.count().filter(OutboxEvent.status.in_(("pending", "running", "failed"))),
                    func.count().filter(OutboxEvent.status == "dead_letter"),
                    func.min(OutboxEvent.next_attempt_at).filter(
                        OutboxEvent.status.in_(("pending", "running", "failed"))
                    ),
                ).where(OutboxEvent.target_backend == "memory_agent_http")
            )
        ).one()
    oldest = row[2]
    return {
        "outbox_backlog": row[0] or 0,
        "outbox_dead_letters": row[1] or 0,
        "oldest_outbox_age_seconds": (
            max(0.0, (datetime.now(UTC) - oldest).total_seconds()) if oldest else 0.0
        ),
    }


async def _run() -> None:
    try:
        print(json.dumps(await _snapshot(), sort_keys=True))
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Report safe Memory Agent Outbox diagnostics")
    parser.parse_args()
    asyncio.run(_run())


if __name__ == "__main__":
    main()
