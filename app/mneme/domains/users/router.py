import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.database import get_database, get_write_database
from app.mneme.crud.document import list_documents
from app.mneme.crud.knowledge_base import (
    create_knowledge_base,
    get_knowledge_base_by_id,
    list_knowledge_bases_by_user_id,
)
from app.mneme.domains.documents.resources import delete_knowledge_base_resources
from app.mneme.domains.tasks.outbox import enqueue_graph_projection_upsert
from app.mneme.models.user import User
from app.mneme.schemas.knowledge_base import (
    KnowledgeBaseCreateRequest,
    KnowledgeBaseData,
    KnowledgeBaseDeleteData,
    KnowledgeBaseListData,
)
from app.mneme.utils.auth import get_current_user
from app.mneme.utils.exceptions import BusinessException
from app.mneme.utils.response import success_response

router = APIRouter(prefix="/users", tags=["users"])


def build_knowledge_base_id() -> str:
    return f"kb_{uuid.uuid4().hex[:12]}"


def ensure_current_user_matches(current_user: User, user_id: int) -> None:
    if current_user.id != user_id:
        raise BusinessException(message="you do not have access to this user resource", code=4007, status_code=403)


@router.post("/{user_id}/knowledge-bases")
async def create_knowledge_base_api(
        user_id: int,
        payload: KnowledgeBaseCreateRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_write_database),
):
    ensure_current_user_matches(current_user, user_id)

    knowledge_base = await create_knowledge_base(
        db,
        knowledge_base_id=build_knowledge_base_id(),
        user_id=user_id,
        name=payload.name,
        description=payload.description,
        is_default=False,
    )
    await enqueue_graph_projection_upsert(
        db,
        aggregate_type="knowledge_base",
        aggregate_id=knowledge_base.id,
        operation_id=knowledge_base.created_at.isoformat(),
    )
    data = KnowledgeBaseData.model_validate(knowledge_base)
    return success_response(data=data, message="knowledge base created")


@router.get("/{user_id}/knowledge-bases")
async def list_knowledge_bases_api(
        user_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    ensure_current_user_matches(current_user, user_id)

    knowledge_bases = await list_knowledge_bases_by_user_id(db, user_id=user_id)
    items = [KnowledgeBaseData.model_validate(item) for item in knowledge_bases]
    data = KnowledgeBaseListData(items=items, total=len(items))
    return success_response(data=data)


@router.delete("/{user_id}/knowledge-bases/{knowledge_base_id}")
async def delete_knowledge_base_api(
        user_id: int,
        knowledge_base_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_write_database),
):
    ensure_current_user_matches(current_user, user_id)

    knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id)
    if not knowledge_base or knowledge_base.user_id != user_id:
        raise BusinessException(message="knowledge base not found", code=4042, status_code=404)

    if knowledge_base.is_default:
        raise BusinessException(message="default knowledge base cannot be deleted", code=4022, status_code=400)

    documents = await list_documents(
        db,
        knowledge_base_pk=knowledge_base.pk,
    )
    active_statuses = {
        "queued",
        "indexing",
        "parsing",
        "chunking",
        "embedding",
        "vector_upserting",
    }
    if any(doc.status in active_statuses for doc in documents):
        raise BusinessException(
            message="knowledge base has active indexing documents; retry later",
            code=4023,
            status_code=400,
        )

    result = await delete_knowledge_base_resources(
        db,
        knowledge_base_id=knowledge_base.id,
        knowledge_base_pk=knowledge_base.pk,
    )
    return success_response(
        data=KnowledgeBaseDeleteData(**result),
        message="knowledge base deleted",
    )
