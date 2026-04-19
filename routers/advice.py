from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from conf.database import get_database
from conf.logging import app_logger
from crud.knowledge_base import get_knowledge_base_by_id
from models.user import User
from schemas.advice import GrowthAdviceRequest, GrowthAdviceResult
from services.insight_service import build_advice_for_knowledge_base
from utils.auth import get_current_user
from utils.exceptions import BusinessException
from utils.response import success_response


router = APIRouter(prefix="/advice", tags=["advice"])


@router.post("/knowledge-bases/{knowledge_base_id}")
async def get_growth_advice(
        knowledge_base_id: str,
        payload: GrowthAdviceRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="advice_router").info(
        f"growth advice request knowledge_base_id={knowledge_base_id} current_user_id={current_user.id}"
    )

    knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id)
    if not knowledge_base:
        raise BusinessException(message="知识库不存在", code=4042, status_code=404)

    if knowledge_base.user_id != current_user.id:
        raise BusinessException(message="知识库不属于该用户", code=4007)

    entries, _, _, advice = await build_advice_for_knowledge_base(
        db,
        user_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        focus_goal=payload.focus_goal,
    )

    data = GrowthAdviceResult(**advice)
    app_logger.bind(module="advice_router").info(
        f"growth advice success knowledge_base_id={knowledge_base_id} current_user_id={current_user.id} "
        f"entry_count={len(entries)}"
    )
    return success_response(data=data)
