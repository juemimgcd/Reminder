import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from conf.database import get_database
from crud.document import list_documents
from crud.knowledge_base import create_knowledge_base, get_knowledge_base_by_id, list_knowledge_bases_by_user_id
from models.user import User
from schemas.knowledge_base import (
    KnowledgeBaseCreateRequest,
    KnowledgeBaseData,
    KnowledgeBaseDeleteData,
    KnowledgeBaseListData,
)
from services.graph_projection_service import sync_knowledge_base_projection
from services.resource_service import delete_knowledge_base_resources
from utils.auth import get_current_user
from utils.exceptions import BusinessException
from utils.response import success_response

router = APIRouter(prefix="/users", tags=["users"])


def build_knowledge_base_id() -> str:
    return f"kb_{uuid.uuid4().hex[:12]}"


def ensure_current_user_matches(current_user: User, user_id: int) -> None:
    if current_user.id != user_id:
        raise BusinessException(message="你无权访问该用户资源", code=4007, status_code=403)


@router.post("/{user_id}/knowledge-bases")
async def create_knowledge_base_api(
        user_id: int,
        payload: KnowledgeBaseCreateRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
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
    await sync_knowledge_base_projection(user=current_user, knowledge_base=knowledge_base)
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
        db: AsyncSession = Depends(get_database),
):
    ensure_current_user_matches(current_user, user_id)

    knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id)
    if not knowledge_base or knowledge_base.user_id != user_id:
        raise BusinessException(message="知识库不存在", code=4042, status_code=404)

    if knowledge_base.is_default:
        raise BusinessException(message="默认知识库不能删除", code=4022, status_code=400)

    documents = await list_documents(
        db,
        knowledge_base_pk=knowledge_base.pk,
    )
    if any(doc.status in {"queued", "indexing", "parsing", "chunking", "embedding", "vector_upserting"} for doc in documents):
        raise BusinessException(message="知识库中仍有文档在索引中，暂时不能删除", code=4023, status_code=400)

    result = await delete_knowledge_base_resources(
        db,
        knowledge_base_id=knowledge_base.id,
        knowledge_base_pk=knowledge_base.pk,
    )
    await db.commit()
    return success_response(
        data=KnowledgeBaseDeleteData(**result),
        message="knowledge base deleted",
    )
