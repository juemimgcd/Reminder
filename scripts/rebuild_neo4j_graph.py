import asyncio

from conf.database import AsyncSessionLocal
from crud.user import list_users
from services.graph_admin_service import rebuild_graph_projection_for_user


async def rebuild_neo4j_graph() -> None:
    async with AsyncSessionLocal() as db:
        users = await list_users(db)
        for user in users:
            await rebuild_graph_projection_for_user(
                db,
                current_user=user,
            )


if __name__ == "__main__":
    asyncio.run(rebuild_neo4j_graph())
