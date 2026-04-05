import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from conf.database import get_database
from crud.knowledge_base import create_knowledge_base, list_knowledge_bases_by_user_id
from crud.user import get_user_by_id, list_users
from schemas.knowledge_base import (
    KnowledgeBaseCreateRequest,
    KnowledgeBaseData,
    KnowledgeBaseListData,
)
from schemas.user import UserCreateRequest, UserData, UserListData
from utils.exceptions import BusinessException
from utils.response import success_response

router = APIRouter(prefix="/users", tags=["users"])


def build_knowledge_base_id() -> str:
    return f"kb_{uuid.uuid4().hex[:12]}"


@router.post("")
async def create_user_api(
        payload: UserCreateRequest,
        db: AsyncSession = Depends(get_database),
):
    _ = payload
    _ = db
    raise BusinessException(
        message="请使用 /auth/register 完成用户注册",
        code=4017,
        status_code=400,
    )


@router.get("")
async def list_users_api(db: AsyncSession = Depends(get_database)):
    users = await list_users(db)
    items = [UserData.model_validate(item) for item in users]
    data = UserListData(items=items, total=len(items))
    return success_response(data=data)


@router.post("/{user_id}/knowledge-bases")
async def create_knowledge_base_api(
        user_id: int,
        payload: KnowledgeBaseCreateRequest,
        db: AsyncSession = Depends(get_database),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise BusinessException(message="用户不存在", code=4041, status_code=404)

    knowledge_base = await create_knowledge_base(
        db,
        knowledge_base_id=build_knowledge_base_id(),
        user_id=user_id,
        name=payload.name,
        description=payload.description,
        is_default=False,
    )
    data = KnowledgeBaseData.model_validate(knowledge_base)
    return success_response(data=data, message="knowledge base created")


@router.get("/{user_id}/knowledge-bases")
async def list_knowledge_bases_api(
        user_id: int,
        db: AsyncSession = Depends(get_database),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise BusinessException(message="用户不存在", code=4041, status_code=404)

    knowledge_bases = await list_knowledge_bases_by_user_id(db, user_id=user_id)
    items = [KnowledgeBaseData.model_validate(item) for item in knowledge_bases]
    data = KnowledgeBaseListData(items=items, total=len(items))
    return success_response(data=data)
