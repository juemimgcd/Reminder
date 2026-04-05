from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from conf.database import get_database
from crud.knowledge_base import get_knowledge_base_by_id
from crud.user import get_user_by_id
from schemas.chat import ChatQueryData, ChatQueryRequest
from utils.exceptions import BusinessException
from utils.rag_service import generate_rag_answer
from utils.response import success_response


router = APIRouter(prefix="/kb/chat", tags=["chat"])


@router.post("/query")
async def query_chat(
        payload: ChatQueryRequest,
        db: AsyncSession = Depends(get_database),
):
    user = await get_user_by_id(db, payload.user_id)
    if not user:
        raise BusinessException(message="用户不存在", code=4041, status_code=404)

    knowledge_base = await get_knowledge_base_by_id(db, payload.knowledge_base_id)
    if not knowledge_base:
        raise BusinessException(message="知识库不存在", code=4042, status_code=404)

    if knowledge_base.user_id != payload.user_id:
        raise BusinessException(message="知识库不属于该用户", code=4007)

    result = await generate_rag_answer(
        question=payload.question,
        knowledge_base_id=payload.knowledge_base_id,
        user_id=payload.user_id,
        top_k=payload.top_k,
    )
    data = ChatQueryData(**result)
    return success_response(data=data)
