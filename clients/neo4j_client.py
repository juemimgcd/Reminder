import asyncio
from typing import Any

from conf.config import settings

try:
    from neo4j import AsyncGraphDatabase
except ImportError:  # pragma: no cover - optional dependency at runtime
    AsyncGraphDatabase = None


_driver = None
_driver_lock = asyncio.Lock()
_schema_ready = False
_schema_lock = asyncio.Lock()

_CONSTRAINTS = (
    "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (n:User) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT knowledge_base_id_unique IF NOT EXISTS FOR (n:KnowledgeBase) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (n:Document) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT memory_entry_id_unique IF NOT EXISTS FOR (n:MemoryEntry) REQUIRE n.id IS UNIQUE",
)


def is_neo4j_projection_enabled() -> bool:
    return settings.NEO4J_ENABLED


def should_use_neo4j_graph_backend() -> bool:
    return settings.GRAPH_BACKEND.lower() == "neo4j"


async def get_neo4j_driver():
    global _driver

    if _driver is not None:
        return _driver

    async with _driver_lock:
        if _driver is not None:
            return _driver
        if AsyncGraphDatabase is None:
            raise RuntimeError("neo4j package is not installed")

        auth = None
        if settings.NEO4J_USER:
            auth = (settings.NEO4J_USER, settings.NEO4J_PASSWORD)

        _driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=auth,
            max_connection_pool_size=settings.NEO4J_MAX_CONNECTION_POOL_SIZE,
        )
        return _driver


async def ensure_neo4j_schema() -> None:
    global _schema_ready

    if _schema_ready:
        return

    async with _schema_lock:
        if _schema_ready:
            return

        driver = await get_neo4j_driver()
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            for statement in _CONSTRAINTS:
                cursor = await session.run(statement)
                await cursor.consume()

        _schema_ready = True


async def run_neo4j_write(statement: str, parameters: dict[str, Any] | None = None) -> None:
    driver = await get_neo4j_driver()
    await ensure_neo4j_schema()

    async with driver.session(database=settings.NEO4J_DATABASE) as session:
        cursor = await session.run(statement, parameters or {})
        await cursor.consume()


async def fetch_neo4j_records(
        statement: str,
        parameters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    driver = await get_neo4j_driver()
    await ensure_neo4j_schema()

    async with driver.session(database=settings.NEO4J_DATABASE) as session:
        cursor = await session.run(statement, parameters or {})
        return [record.data() async for record in cursor]


async def probe_neo4j() -> dict[str, Any]:
    if not is_neo4j_projection_enabled():
        return {
            "enabled": False,
            "backend": settings.GRAPH_BACKEND.lower(),
            "database": settings.NEO4J_DATABASE,
            "uri": settings.NEO4J_URI,
            "ok": False,
            "error": "neo4j projection is disabled",
        }

    try:
        driver = await get_neo4j_driver()
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            cursor = await session.run("RETURN 1 AS ok")
            record = await cursor.single()

        return {
            "enabled": True,
            "backend": settings.GRAPH_BACKEND.lower(),
            "database": settings.NEO4J_DATABASE,
            "uri": settings.NEO4J_URI,
            "ok": bool(record and record.get("ok") == 1),
            "error": None,
        }
    except Exception as exc:  # pragma: no cover - depends on external service
        return {
            "enabled": True,
            "backend": settings.GRAPH_BACKEND.lower(),
            "database": settings.NEO4J_DATABASE,
            "uri": settings.NEO4J_URI,
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


async def close_neo4j_driver() -> None:
    global _driver, _schema_ready

    if _driver is None:
        return

    await _driver.close()
    _driver = None
    _schema_ready = False
