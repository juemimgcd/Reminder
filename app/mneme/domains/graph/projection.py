from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.clients.neo4j_client import is_neo4j_projection_enabled, run_neo4j_write
from app.mneme.conf.logging import app_logger
from app.mneme.crud.document import list_documents
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id
from app.mneme.crud.memory_entry import list_memory_entries_by_user_id
from app.mneme.crud.user import get_user_by_id
from app.mneme.domains.graph.service import _build_related_document_edges


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _document_node_id(document_id: str) -> str:
    return f"document:{document_id}"


def _memory_node_id(entry_id: str) -> str:
    return f"memory_entry:{entry_id}"


async def _execute_projection_write(
        *,
        action: str,
        statement: str,
        parameters: dict,
        raise_on_error: bool = False,
) -> None:
    if not is_neo4j_projection_enabled():
        return

    try:
        await run_neo4j_write(statement, parameters)
    except Exception as exc:  # pragma: no cover - depends on external service
        app_logger.bind(module="graph_projection").exception(
            f"neo4j projection {action} failed error_type={type(exc).__name__} error={exc}"
        )
        if raise_on_error:
            raise


async def sync_user_projection(*, user, raise_on_error: bool = False) -> None:
    await _execute_projection_write(
        action="sync_user",
        statement="""
        MERGE (u:User {id: $user.id})
        SET u.username = $user.username,
            u.display_name = $user.display_name,
            u.avatar_url = $user.avatar_url,
            u.created_at = $user.created_at,
            u.updated_at = $user.updated_at,
            u.last_login_at = $user.last_login_at
        """,
        parameters={
            "user": {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "created_at": _to_iso(user.created_at),
                "updated_at": _to_iso(user.updated_at),
                "last_login_at": _to_iso(getattr(user, "last_login_at", None)),
            }
        },
        raise_on_error=raise_on_error,
    )


async def sync_knowledge_base_projection(*, user, knowledge_base, raise_on_error: bool = False) -> None:
    await _execute_projection_write(
        action="sync_knowledge_base",
        statement="""
        MERGE (u:User {id: $user.id})
        SET u.username = $user.username,
            u.display_name = $user.display_name,
            u.avatar_url = $user.avatar_url,
            u.created_at = $user.created_at,
            u.updated_at = $user.updated_at,
            u.last_login_at = $user.last_login_at
        MERGE (kb:KnowledgeBase {id: $knowledge_base.id})
        SET kb.user_id = $knowledge_base.user_id,
            kb.name = $knowledge_base.name,
            kb.description = $knowledge_base.description,
            kb.is_default = $knowledge_base.is_default,
            kb.created_at = $knowledge_base.created_at,
            kb.updated_at = $knowledge_base.updated_at
        MERGE (u)-[:OWNS]->(kb)
        """,
        parameters={
            "user": {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "created_at": _to_iso(user.created_at),
                "updated_at": _to_iso(user.updated_at),
                "last_login_at": _to_iso(getattr(user, "last_login_at", None)),
            },
            "knowledge_base": {
                "id": knowledge_base.id,
                "user_id": knowledge_base.user_id,
                "name": knowledge_base.name,
                "description": knowledge_base.description,
                "is_default": knowledge_base.is_default,
                "created_at": _to_iso(knowledge_base.created_at),
                "updated_at": _to_iso(knowledge_base.updated_at),
            },
        },
        raise_on_error=raise_on_error,
    )


async def sync_document_projection(*, user, knowledge_base, document, raise_on_error: bool = False) -> None:
    await _execute_projection_write(
        action="sync_document",
        statement="""
        MERGE (u:User {id: $user.id})
        SET u.username = $user.username,
            u.display_name = $user.display_name,
            u.avatar_url = $user.avatar_url,
            u.created_at = $user.created_at,
            u.updated_at = $user.updated_at,
            u.last_login_at = $user.last_login_at
        MERGE (kb:KnowledgeBase {id: $knowledge_base.id})
        SET kb.user_id = $knowledge_base.user_id,
            kb.name = $knowledge_base.name,
            kb.description = $knowledge_base.description,
            kb.is_default = $knowledge_base.is_default,
            kb.created_at = $knowledge_base.created_at,
            kb.updated_at = $knowledge_base.updated_at
        MERGE (u)-[:OWNS]->(kb)
        MERGE (d:Document {id: $document.id})
        SET d.user_id = $document.user_id,
            d.knowledge_base_id = $document.knowledge_base_id,
            d.file_name = $document.file_name,
            d.file_type = $document.file_type,
            d.file_size = $document.file_size,
            d.status = $document.status,
            d.created_at = $document.created_at,
            d.updated_at = $document.updated_at
        MERGE (kb)-[:CONTAINS]->(d)
        """,
        parameters={
            "user": {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "created_at": _to_iso(user.created_at),
                "updated_at": _to_iso(user.updated_at),
                "last_login_at": _to_iso(getattr(user, "last_login_at", None)),
            },
            "knowledge_base": {
                "id": knowledge_base.id,
                "user_id": knowledge_base.user_id,
                "name": knowledge_base.name,
                "description": knowledge_base.description,
                "is_default": knowledge_base.is_default,
                "created_at": _to_iso(knowledge_base.created_at),
                "updated_at": _to_iso(knowledge_base.updated_at),
            },
            "document": {
                "id": document.id,
                "user_id": document.user_id,
                "knowledge_base_id": document.knowledge_base_id,
                "file_name": document.file_name,
                "file_type": document.file_type,
                "file_size": document.file_size,
                "status": document.status,
                "created_at": _to_iso(document.created_at),
                "updated_at": _to_iso(document.updated_at),
            },
        },
        raise_on_error=raise_on_error,
    )


async def sync_document_projection_from_db(
        db: AsyncSession,
        *,
        document,
) -> None:
    knowledge_base = await get_knowledge_base_by_id(
        db,
        knowledge_base_id=document.knowledge_base_id,
    )
    user = await get_user_by_id(
        db,
        user_id=document.user_id,
    )
    if not knowledge_base or not user:
        return

    await sync_document_projection(
        user=user,
        knowledge_base=knowledge_base,
        document=document,
    )


async def sync_document_memory_projection(
        db: AsyncSession,
        *,
        user,
        knowledge_base,
        document,
        memory_entries: list,
        rebuild_related_edges: bool = True,
        raise_on_error: bool = False,
) -> None:
    if not is_neo4j_projection_enabled():
        return

    await sync_document_projection(
        user=user,
        knowledge_base=knowledge_base,
        document=document,
        raise_on_error=raise_on_error,
    )

    await _execute_projection_write(
        action="replace_document_memory",
        statement="""
        MATCH (d:Document {id: $document_id})
        OPTIONAL MATCH (d)-[:EXTRACTS]->(m:MemoryEntry)
        DETACH DELETE m
        """,
        parameters={"document_id": document.id},
        raise_on_error=raise_on_error,
    )

    if memory_entries:
        await _execute_projection_write(
            action="upsert_document_memory",
            statement="""
            MATCH (d:Document {id: $document_id})
            UNWIND $entries AS entry
            MERGE (m:MemoryEntry {id: entry.id})
            SET m.user_id = entry.user_id,
                m.knowledge_base_id = entry.knowledge_base_id,
                m.document_id = entry.document_id,
                m.chunk_id = entry.chunk_id,
                m.entry_name = entry.entry_name,
                m.entry_type = entry.entry_type,
                m.summary = entry.summary,
                m.evidence_text = entry.evidence_text,
                m.importance_score = entry.importance_score,
                m.created_at = entry.created_at,
                m.updated_at = entry.updated_at
            MERGE (d)-[:EXTRACTS]->(m)
            """,
            parameters={
                "document_id": document.id,
                "entries": [
                    {
                        "id": entry.id,
                        "user_id": entry.user_id,
                        "knowledge_base_id": entry.knowledge_base_id,
                        "document_id": entry.document_id,
                        "chunk_id": entry.chunk_id,
                        "entry_name": entry.entry_name,
                        "entry_type": entry.entry_type,
                        "summary": entry.summary,
                        "evidence_text": entry.evidence_text,
                        "importance_score": entry.importance_score,
                        "created_at": _to_iso(entry.created_at),
                        "updated_at": _to_iso(entry.updated_at),
                    }
                    for entry in memory_entries
                ],
            },
            raise_on_error=raise_on_error,
        )

    if rebuild_related_edges:
        await rebuild_user_related_projection(db, user_id=user.id, raise_on_error=raise_on_error)


async def rebuild_user_related_projection(
        db: AsyncSession,
        *,
        user_id: int,
        raise_on_error: bool = False,
) -> None:
    if not is_neo4j_projection_enabled():
        return

    documents = await list_documents(
        db,
        user_id=user_id,
    )
    memory_entries = await list_memory_entries_by_user_id(
        db,
        user_id=user_id,
    )
    related_edges = _build_related_document_edges(
        documents=documents,
        memory_entries=memory_entries,
        min_shared_memory_count=1,
        min_relationship_score=0.0,
        max_related_edges=None,
    )

    await _execute_projection_write(
        action="clear_user_related_edges",
        statement="""
        MATCH (:User {id: $user_id})-[:OWNS]->(:KnowledgeBase)-[:CONTAINS]->(d:Document)
        OPTIONAL MATCH (d)-[r:RELATED]-(:Document)
        WITH DISTINCT r
        WHERE r IS NOT NULL
        DELETE r
        """,
        parameters={"user_id": user_id},
        raise_on_error=raise_on_error,
    )

    if not related_edges:
        return

    await _execute_projection_write(
        action="upsert_user_related_edges",
        statement="""
        UNWIND $edges AS edge
        MATCH (source:Document {id: edge.source_document_id})
        MATCH (target:Document {id: edge.target_document_id})
        MERGE (source)-[r:RELATED]->(target)
        SET r = edge.metadata
        """,
        parameters={
            "edges": [
                {
                    "source_document_id": edge["source"].removeprefix("document:"),
                    "target_document_id": edge["target"].removeprefix("document:"),
                    "metadata": edge["metadata"],
                }
                for edge in related_edges
            ]
        },
        raise_on_error=raise_on_error,
    )


async def delete_document_projection(*, document_id: str) -> None:
    await _execute_projection_write(
        action="delete_document",
        statement="""
        MATCH (d:Document {id: $document_id})
        DETACH DELETE d
        """,
        parameters={"document_id": document_id},
    )


async def delete_knowledge_base_projection(*, knowledge_base_id: str) -> None:
    await _execute_projection_write(
        action="delete_knowledge_base",
        statement="""
        MATCH (kb:KnowledgeBase {id: $knowledge_base_id})
        DETACH DELETE kb
        """,
        parameters={"knowledge_base_id": knowledge_base_id},
    )


async def reset_user_projection(*, user_id: int) -> None:
    await _execute_projection_write(
        action="reset_user",
        statement="""
        MATCH (u:User {id: $user_id})
        DETACH DELETE u
        """,
        parameters={"user_id": user_id},
    )
