from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from conf.database import get_database
from conf.logging import app_logger
from crud.memory_entry import (
    list_memory_entries_by_document_id,
    list_memory_entries_by_knowledge_base_id,
    list_memory_entries_by_user_id,
)
from crud.document import get_document_by_id, list_documents
from crud.knowledge_base import get_knowledge_base_by_id, list_knowledge_bases_by_user_id
from models.user import User
from schemas.graph import GraphData
from services.graph_service import (
    build_document_graph_payload,
    build_knowledge_base_graph_payload,
    build_user_graph_payload,
)
from utils.auth import get_current_user
from utils.exceptions import BusinessException
from utils.response import success_response


router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("")
async def get_user_graph(
        include_memory: bool = Query(default=False, description="是否返回 memory_entry 节点"),
        include_relationships: bool = Query(default=False, description="是否返回文档关联边"),
        min_shared_memory_count: int = Query(default=2, ge=1, le=20, description="生成关联边时最少共享的 memory 数"),
        min_relationship_score: float = Query(default=0.35, ge=0, le=1, description="保留关联边所需的最小分数"),
        max_related_edges: int = Query(default=80, ge=1, le=500, description="最多返回多少条关联边"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="graph_router").info(
        f"graph request scope=user current_user_id={current_user.id} "
        f"include_memory={include_memory} include_relationships={include_relationships} "
        f"min_shared_memory_count={min_shared_memory_count} min_relationship_score={min_relationship_score} "
        f"max_related_edges={max_related_edges}"
    )
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
        include_memory: bool = Query(default=False, description="是否返回当前文档的 memory_entry 节点"),
        include_relationships: bool = Query(default=False, description="是否返回与当前文档关联的其他文档边"),
        min_shared_memory_count: int = Query(default=2, ge=1, le=20, description="生成关联边时最少共享的 memory 数"),
        min_relationship_score: float = Query(default=0.35, ge=0, le=1, description="保留关联边所需的最小分数"),
        max_related_edges: int = Query(default=24, ge=1, le=200, description="当前文档最多返回多少条关联边"),
        relationship_scope: str = Query(default="knowledge_base", pattern="^(knowledge_base|user)$", description="关联文档搜索范围"),
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
        raise BusinessException(message="文档不存在或不属于该用户", code=4044, status_code=404)

    root_knowledge_base = await get_knowledge_base_by_id(
        db,
        knowledge_base_id=document.knowledge_base_id,
    )
    if not root_knowledge_base or root_knowledge_base.user_id != current_user.id:
        raise BusinessException(message="知识库不存在或不属于该用户", code=4042, status_code=404)

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
        include_memory: bool = Query(default=False, description="是否返回 memory_entry 节点"),
        include_relationships: bool = Query(default=False, description="是否返回文档关联边"),
        min_shared_memory_count: int = Query(default=2, ge=1, le=20, description="生成关联边时最少共享的 memory 数"),
        min_relationship_score: float = Query(default=0.35, ge=0, le=1, description="保留关联边所需的最小分数"),
        max_related_edges: int = Query(default=80, ge=1, le=500, description="最多返回多少条关联边"),
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
        raise BusinessException(message="知识库不存在", code=4042, status_code=404)
    if knowledge_base.user_id != current_user.id:
        raise BusinessException(message="知识库不属于该用户", code=4007, status_code=403)

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
