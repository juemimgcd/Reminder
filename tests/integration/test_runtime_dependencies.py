import asyncio
import os
from uuid import uuid4

import asyncpg
import pytest
from redis.asyncio import Redis

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="set RUN_INTEGRATION_TESTS=1 with PostgreSQL and Redis test DSNs",
    ),
]


def test_postgresql_migrations_and_transaction_round_trip():
    async def execute() -> None:
        connection = await asyncpg.connect(os.environ["TEST_POSTGRES_DSN"])
        try:
            revision_count = await connection.fetchval("SELECT count(*) FROM alembic_version")
            assert revision_count == 1

            transaction = connection.transaction()
            await transaction.start()
            try:
                await connection.execute("CREATE TEMP TABLE mneme_integration_probe (value text NOT NULL)")
                await connection.execute("INSERT INTO mneme_integration_probe (value) VALUES ('ready')")
                assert await connection.fetchval("SELECT value FROM mneme_integration_probe") == "ready"
            finally:
                await transaction.rollback()
        finally:
            await connection.close()

    asyncio.run(execute())


def test_redis_round_trip_is_isolated_and_cleaned_up():
    async def execute() -> None:
        client = Redis.from_url(os.environ["TEST_REDIS_URL"], decode_responses=True)
        key = f"mneme:integration:{uuid4().hex}"
        try:
            assert await client.ping() is True
            assert await client.set(key, "ready", ex=30) is True
            assert await client.get(key) == "ready"
            assert await client.delete(key) == 1
        finally:
            await client.aclose()

    asyncio.run(execute())
