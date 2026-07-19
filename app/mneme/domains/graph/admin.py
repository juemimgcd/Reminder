from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.clients.neo4j_client import is_neo4j_projection_enabled, probe_neo4j
from app.mneme.crud.document import list_documents
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id, list_knowledge_bases_by_user_id
from app.mneme.crud.memory_entry import list_memory_entries_by_document_id
from app.mneme.domains.graph.projection import (
    rebuild_user_related_projection,
    reset_user_projection,
    sync_document_memory_projection,
    sync_knowledge_base_projection,
    sync_user_projection,
)
from app.mneme.models.user import User
from app.mneme.utils.exceptions import BusinessException


async def get_neo4j_health_status() -> dict:
    return await probe_neo4j()


async def rebuild_graph_projection_for_user(
        db: AsyncSession,
        *,
        current_user: User,
) -> dict[str, int | str]:
    if not is_neo4j_projection_enabled():
        raise BusinessException(message="Neo4j graph projection is not enabled", code=5031, status_code=503)

    await reset_user_projection(user_id=current_user.id)
    await sync_user_projection(user=current_user)

    knowledge_bases = await list_knowledge_bases_by_user_id(
        db,
        user_id=current_user.id,
    )
    document_count = 0
    memory_entry_count = 0

    for knowledge_base in knowledge_bases:
        await sync_knowledge_base_projection(
            user=current_user,
            knowledge_base=knowledge_base,
        )
        documents = await list_documents(
            db,
            user_id=current_user.id,
            knowledge_base_pk=knowledge_base.pk,
        )
        for document in documents:
            memory_entries = await list_memory_entries_by_document_id(
                db,
                document_id=document.id,
            )
            await sync_document_memory_projection(
                db,
                user=current_user,
                knowledge_base=knowledge_base,
                document=document,
                memory_entries=memory_entries,
                rebuild_related_edges=False,
            )
            document_count += 1
            memory_entry_count += len(memory_entries)

    await rebuild_user_related_projection(
        db,
        user_id=current_user.id,
    )

    return {
        "scope": "user",
        "user_id": current_user.id,
        "knowledge_base_count": len(knowledge_bases),
        "document_count": document_count,
        "memory_entry_count": memory_entry_count,
        "status": "completed",
    }


async def rebuild_graph_projection_for_knowledge_base(
        db: AsyncSession,
        *,
        current_user: User,
        knowledge_base_id: str,
) -> dict[str, int | str]:
    if not is_neo4j_projection_enabled():
        raise BusinessException(message="Neo4j graph projection is not enabled", code=5031, status_code=503)

    knowledge_base = await get_knowledge_base_by_id(
        db,
        knowledge_base_id=knowledge_base_id,
    )
    if not knowledge_base or knowledge_base.user_id != current_user.id:
        raise BusinessException(
            message="knowledge base not found or not owned by current user",
            code=4042,
            status_code=404,
        )

    await sync_user_projection(user=current_user)
    await sync_knowledge_base_projection(
        user=current_user,
        knowledge_base=knowledge_base,
    )

    documents = await list_documents(
        db,
        user_id=current_user.id,
        knowledge_base_pk=knowledge_base.pk,
    )
    memory_entry_count = 0
    for document in documents:
        memory_entries = await list_memory_entries_by_document_id(
            db,
            document_id=document.id,
        )
        await sync_document_memory_projection(
            db,
            user=current_user,
            knowledge_base=knowledge_base,
            document=document,
            memory_entries=memory_entries,
            rebuild_related_edges=False,
        )
        memory_entry_count += len(memory_entries)

    await rebuild_user_related_projection(
        db,
        user_id=current_user.id,
    )

    return {
        "scope": "knowledge_base",
        "user_id": current_user.id,
        "knowledge_base_id": knowledge_base.id,
        "document_count": len(documents),
        "memory_entry_count": memory_entry_count,
        "status": "completed",
    }
