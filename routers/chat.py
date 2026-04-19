from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from conf.config import settings
from conf.database import get_database
from conf.logging import app_logger
from crud.knowledge_base import get_knowledge_base_by_id
from infra.rate_limit import enforce_fixed_window_rate_limit
from models.user import User
from schemas.chat import ChatQueryData, ChatQueryRequest
from services.query_service import generate_rag_answer
from utils.auth import get_current_user
from utils.exceptions import BusinessException
from utils.response import success_response


router = APIRouter(prefix="/kb/chat", tags=["chat"])


@router.post("/query")
async def query_chat(
        payload: ChatQueryRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="chat_router").info(
        f"chat query request user_id={current_user.id} knowledge_base_id={payload.knowledge_base_id} "
        f"top_k={payload.top_k} question_length={len(payload.question)}"
    )

    enforce_fixed_window_rate_limit(
        bucket="chat_query",
        key=f"user:{current_user.id}:kb:{payload.knowledge_base_id}",
        limit=settings.CHAT_QUERY_RATE_LIMIT_MAX,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )

    knowledge_base = await get_knowledge_base_by_id(db, payload.knowledge_base_id)
    if not knowledge_base:
        raise BusinessException(message="知识库不存在", code=4042, status_code=404)

    if knowledge_base.user_id != current_user.id:
        raise BusinessException(message="知识库不属于该用户", code=4007)

    result = await generate_rag_answer(
        question=payload.question,
        knowledge_base_id=payload.knowledge_base_id,
        user_id=current_user.id,
        top_k=payload.top_k,
    )
    app_logger.bind(module="chat_router").info(
        f"chat query success user_id={current_user.id} knowledge_base_id={payload.knowledge_base_id} "
        f"source_count={len(result['sources'])}"
    )
    data = ChatQueryData(**result)
    return success_response(data=data)
