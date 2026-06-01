from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.database import get_database
from app.mneme.conf.logging import app_logger
from app.mneme.crud.memory_entry import (
    list_memory_entries_by_document_id,
    list_memory_entries_by_knowledge_base_id,
    list_memory_entries_by_user_id,
)
from app.mneme.crud.document import get_document_by_id, list_documents
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id, list_knowledge_bases_by_user_id
from app.mneme.models.user import User
from app.mneme.schemas.graph_admin import GraphProjectionRebuildData
from app.mneme.schemas.graph import GraphData
from app.mneme.schemas.graph_rag import GraphRagDecisionData
from app.mneme.services.graph_admin_service import (
    rebuild_graph_projection_for_knowledge_base,
    rebuild_graph_projection_for_user,
)
from app.mneme.services.graph_query_service import (
    build_document_graph_payload_from_neo4j,
    build_knowledge_base_graph_payload_from_neo4j,
    build_user_graph_payload_from_neo4j,
)
from app.mneme.services.graph_service import (
    build_document_graph_payload,
    build_knowledge_base_graph_payload,
    build_user_graph_payload,
)
from app.mneme.services.graph_rag_service import build_graph_rag_decision
from app.mneme.utils.auth import get_current_user
from app.mneme.utils.exceptions import BusinessException
from app.mneme.utils.response import success_response


router = APIRouter(prefix="/graph", tags=["graph"])


@router.post("/rebuild")
async def rebuild_user_graph_projection_api(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="graph_router").info(
        f"graph rebuild request scope=user current_user_id={current_user.id}"
    )
    result = await rebuild_graph_projection_for_user(
        db,
        current_user=current_user,
    )
    app_logger.bind(module="graph_router").info(
        f"graph rebuild success scope=user current_user_id={current_user.id} "
        f"knowledge_base_count={result.get('knowledge_base_count')} "
        f"document_count={result['document_count']} memory_entry_count={result['memory_entry_count']}"
    )
    return success_response(
        data=GraphProjectionRebuildData(**result),
        message="graph projection rebuilt",
    )


@router.get("")
async def get_user_graph(
        include_memory: bool = Query(default=False, description="include memory nodes"),
        include_relationships: bool = Query(default=False, description="include relationship edges"),
        min_shared_memory_count: int = Query(default=2, ge=1, le=20, description="minimum shared memory count"),
        min_relationship_score: float = Query(default=0.35, ge=0, le=1, description="minimum relationship score"),
        max_related_edges: int = Query(default=80, ge=1, le=500, description="maximum related edges"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="graph_router").info(
        f"graph request scope=user current_user_id={current_user.id} "
        f"include_memory={include_memory} include_relationships={include_relationships} "
        f"min_shared_memory_count={min_shared_memory_count} min_relationship_score={min_relationship_score} "
        f"max_related_edges={max_related_edges}"
    )
    neo4j_payload = await build_user_graph_payload_from_neo4j(
        current_user=current_user,
        include_memory=include_memory,
        include_relationships=include_relationships,
        min_shared_memory_count=min_shared_memory_count,
        min_relationship_score=min_relationship_score,
        max_related_edges=max_related_edges,
    )
    if neo4j_payload is not None:
        app_logger.bind(module="graph_router").info(
            f"graph success scope=user current_user_id={current_user.id} "
            f"backend=neo4j node_count={neo4j_payload['node_count']} edge_count={neo4j_payload['edge_count']}"
        )
        return success_response(data=GraphData(**neo4j_payload))

    knowledge_bases = await list_knowledge_bases_by_user_id(
        db,
        user_id=current_user.id,
    )
    documents = await list_documents(
        db,
        user_id=current_user.id,
    )
    memory_entries = []
    if include_memory or include_relationships:
        memory_entries = await list_memory_entries_by_user_id(
            db,
            user_id=current_user.id,
        )
    payload = build_user_graph_payload(
        user=current_user,
        knowledge_bases=knowledge_bases,
        documents=documents,
        memory_entries=memory_entries,
        include_memory=include_memory,
        include_relationships=include_relationships,
        min_shared_memory_count=min_shared_memory_count,
        min_relationship_score=min_relationship_score,
        max_related_edges=max_related_edges,
    )
    app_logger.bind(module="graph_router").info(
        f"graph success scope=user current_user_id={current_user.id} "
        f"knowledge_base_count={len(knowledge_bases)} document_count={len(documents)} "
        f"memory_count={len(memory_entries)} edge_count={payload['edge_count']}"
    )
    return success_response(data=GraphData(**payload))


@router.get("/documents/{document_id}")
async def get_document_graph(
        document_id: str,
        include_memory: bool = Query(default=False, description="include memory nodes"),
        include_relationships: bool = Query(default=False, description="include related document edges"),
        min_shared_memory_count: int = Query(default=2, ge=1, le=20, description="minimum shared memory count"),
        min_relationship_score: float = Query(default=0.35, ge=0, le=1, description="minimum relationship score"),
        max_related_edges: int = Query(default=24, ge=1, le=200, description="maximum related edges"),
        relationship_scope: str = Query(default="knowledge_base", pattern="^(knowledge_base|user)$", description="relationship scope"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="graph_router").info(
        f"graph request scope=document current_user_id={current_user.id} document_id={document_id} "
        f"include_memory={include_memory} include_relationships={include_relationships} "
        f"relationship_scope={relationship_scope} min_shared_memory_count={min_shared_memory_count} "
        f"min_relationship_score={min_relationship_score} max_related_edges={max_related_edges}"
    )
    document = await get_document_by_id(
        db,
        document_id=document_id,
        user_id=current_user.id,
    )
    if not document:
        raise BusinessException(message="document not found or not owned by current user", code=4044, status_code=404)

    root_knowledge_base = await get_knowledge_base_by_id(
        db,
        knowledge_base_id=document.knowledge_base_id,
    )
    if not root_knowledge_base or root_knowledge_base.user_id != current_user.id:
        raise BusinessException(message="knowledge base not found or not owned by current user", code=4042, status_code=404)

    neo4j_payload = await build_document_graph_payload_from_neo4j(
        current_user=current_user,
        root_document=document,
        root_knowledge_base=root_knowledge_base,
        include_memory=include_memory,
        include_relationships=include_relationships,
        min_shared_memory_count=min_shared_memory_count,
        min_relationship_score=min_relationship_score,
        max_related_edges=max_related_edges,
        relationship_scope=relationship_scope,
    )
    if neo4j_payload is not None:
        app_logger.bind(module="graph_router").info(
            f"graph success scope=document current_user_id={current_user.id} document_id={document_id} "
            f"backend=neo4j node_count={neo4j_payload['node_count']} edge_count={neo4j_payload['edge_count']}"
        )
        return success_response(data=GraphData(**neo4j_payload))

    if relationship_scope == "user":
        graph_documents = await list_documents(
            db,
            user_id=current_user.id,
        )
        graph_knowledge_bases = await list_knowledge_bases_by_user_id(
            db,
            user_id=current_user.id,
        )
        relationship_memory_entries = []
        if include_relationships:
            relationship_memory_entries = await list_memory_entries_by_user_id(
                db,
                user_id=current_user.id,
            )
    else:
        graph_documents = await list_documents(
            db,
            user_id=current_user.id,
            knowledge_base_pk=root_knowledge_base.pk,
        )
        graph_knowledge_bases = [root_knowledge_base]
        relationship_memory_entries = []
        if include_relationships:
            relationship_memory_entries = await list_memory_entries_by_knowledge_base_id(
                db,
                knowledge_base_id=root_knowledge_base.id,
            )

    root_memory_entries = []
    if include_memory:
        root_memory_entries = await list_memory_entries_by_document_id(
            db,
            document_id=document.id,
        )

    payload = build_document_graph_payload(
        user=current_user,
        knowledge_bases=graph_knowledge_bases,
        root_document=document,
        documents=graph_documents,
        root_memory_entries=root_memory_entries,
        relationship_memory_entries=relationship_memory_entries,
        include_memory=include_memory,
        include_relationships=include_relationships,
        min_shared_memory_count=min_shared_memory_count,
        min_relationship_score=min_relationship_score,
        max_related_edges=max_related_edges,
        relationship_scope=relationship_scope,
    )
    app_logger.bind(module="graph_router").info(
        f"graph success scope=document current_user_id={current_user.id} document_id={document_id} "
        f"node_count={payload['node_count']} edge_count={payload['edge_count']}"
    )
    return success_response(data=GraphData(**payload))


@router.get("/knowledge-bases/{knowledge_base_id}")
async def get_knowledge_base_graph(
        knowledge_base_id: str,
        include_memory: bool = Query(default=False, description="include memory nodes"),
        include_relationships: bool = Query(default=False, description="include relationship edges"),
        min_shared_memory_count: int = Query(default=2, ge=1, le=20, description="minimum shared memory count"),
        min_relationship_score: float = Query(default=0.35, ge=0, le=1, description="minimum relationship score"),
        max_related_edges: int = Query(default=80, ge=1, le=500, description="maximum related edges"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="graph_router").info(
        f"graph request scope=knowledge_base current_user_id={current_user.id} "
        f"knowledge_base_id={knowledge_base_id} include_memory={include_memory} "
        f"include_relationships={include_relationships} min_shared_memory_count={min_shared_memory_count} "
        f"min_relationship_score={min_relationship_score} max_related_edges={max_related_edges}"
    )
    knowledge_base = await get_knowledge_base_by_id(
        db,
        knowledge_base_id=knowledge_base_id,
    )
    if not knowledge_base:
        raise BusinessException(message="knowledge base not found", code=4042, status_code=404)
    if knowledge_base.user_id != current_user.id:
        raise BusinessException(message="knowledge base does not belong to current user", code=4007, status_code=403)

    neo4j_payload = await build_knowledge_base_graph_payload_from_neo4j(
        current_user=current_user,
        knowledge_base=knowledge_base,
        include_memory=include_memory,
        include_relationships=include_relationships,
        min_shared_memory_count=min_shared_memory_count,
        min_relationship_score=min_relationship_score,
        max_related_edges=max_related_edges,
    )
    if neo4j_payload is not None:
        app_logger.bind(module="graph_router").info(
            f"graph success scope=knowledge_base current_user_id={current_user.id} "
            f"knowledge_base_id={knowledge_base_id} backend=neo4j "
            f"node_count={neo4j_payload['node_count']} edge_count={neo4j_payload['edge_count']}"
        )
        return success_response(data=GraphData(**neo4j_payload))

    documents = await list_documents(
        db,
        user_id=current_user.id,
        knowledge_base_pk=knowledge_base.pk,
    )
    memory_entries = []
    if include_memory or include_relationships:
        memory_entries = await list_memory_entries_by_knowledge_base_id(
            db,
            knowledge_base_id=knowledge_base.id,
        )
    payload = build_knowledge_base_graph_payload(
        user=current_user,
        knowledge_base=knowledge_base,
        documents=documents,
        memory_entries=memory_entries,
        include_memory=include_memory,
        include_relationships=include_relationships,
        min_shared_memory_count=min_shared_memory_count,
        min_relationship_score=min_relationship_score,
        max_related_edges=max_related_edges,
    )
    app_logger.bind(module="graph_router").info(
        f"graph success scope=knowledge_base current_user_id={current_user.id} "
        f"knowledge_base_id={knowledge_base_id} document_count={len(documents)} "
        f"memory_count={len(memory_entries)} edge_count={payload['edge_count']}"
    )
    return success_response(data=GraphData(**payload))


@router.get("/knowledge-bases/{knowledge_base_id}/rag")
async def get_knowledge_base_graph_rag(
        knowledge_base_id: str,
        query: str = Query(..., min_length=1, max_length=500, description="User query for GraphRAG planning"),
        top_k: int = Query(default=6, ge=1, le=20, description="Maximum contexts to return"),
        max_expansions: int = Query(default=8, ge=0, le=50, description="Maximum related document edges"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="graph_router").info(
        f"graph rag request current_user_id={current_user.id} knowledge_base_id={knowledge_base_id} "
        f"top_k={top_k} max_expansions={max_expansions}"
    )
    knowledge_base = await get_knowledge_base_by_id(
        db,
        knowledge_base_id=knowledge_base_id,
    )
    if not knowledge_base:
        raise BusinessException(message="Knowledge base not found.", code=4042, status_code=404)
    if knowledge_base.user_id != current_user.id:
        raise BusinessException(message="Knowledge base does not belong to the current user.", code=4007, status_code=403)

    documents = await list_documents(
        db,
        user_id=current_user.id,
        knowledge_base_pk=knowledge_base.pk,
    )
    memory_entries = await list_memory_entries_by_knowledge_base_id(
        db,
        knowledge_base_id=knowledge_base.id,
    )
    payload = build_graph_rag_decision(
        knowledge_base_id=knowledge_base.id,
        query=query,
        documents=documents,
        entries=memory_entries,
        top_k=top_k,
        max_expansions=max_expansions,
    )
    app_logger.bind(module="graph_router").info(
        f"graph rag success current_user_id={current_user.id} knowledge_base_id={knowledge_base_id} "
        f"seed_count={payload.seed_count} expansion_count={payload.expansion_count} "
        f"context_count={payload.context_count} graph_useful={payload.graph_useful}"
    )
    return success_response(data=GraphRagDecisionData(**payload.model_dump()))


@router.post("/knowledge-bases/{knowledge_base_id}/rebuild")
async def rebuild_knowledge_base_graph_projection_api(
        knowledge_base_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="graph_router").info(
        f"graph rebuild request scope=knowledge_base current_user_id={current_user.id} "
        f"knowledge_base_id={knowledge_base_id}"
    )
    result = await rebuild_graph_projection_for_knowledge_base(
        db,
        current_user=current_user,
        knowledge_base_id=knowledge_base_id,
    )
    app_logger.bind(module="graph_router").info(
        f"graph rebuild success scope=knowledge_base current_user_id={current_user.id} "
        f"knowledge_base_id={knowledge_base_id} document_count={result['document_count']} "
        f"memory_entry_count={result['memory_entry_count']}"
    )
    return success_response(
        data=GraphProjectionRebuildData(**result),
        message="graph projection rebuilt",
    )
