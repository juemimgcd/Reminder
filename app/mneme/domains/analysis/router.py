from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.database import get_database
from app.mneme.conf.logging import app_logger
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id
from app.mneme.domains.analysis.service import build_knowledge_base_analytics_report
from app.mneme.domains.profile.insight import build_growth_for_knowledge_base
from app.mneme.models.user import User
from app.mneme.schemas.analytics import KnowledgeBaseAnalyticsReportData
from app.mneme.schemas.growth_report import GrowthReportResult
from app.mneme.utils.auth import get_current_user
from app.mneme.utils.response import success_response

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/knowledge-bases/{knowledge_base_id}/growth")
async def get_growth_report(
        knowledge_base_id: str,
        recent_days: int = 30,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="analysis_router").info(
        f"growth report request knowledge_base_id={knowledge_base_id} "
        f"current_user_id={current_user.id} recent_days={recent_days}"
    )

    kb = await get_knowledge_base_by_id(db, knowledge_base_id=knowledge_base_id)
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="knowledge_base not found")

    if kb.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="you have no right")

    entries, _, report = await build_growth_for_knowledge_base(
        db,
        user_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        recent_days=recent_days,
    )
    data = GrowthReportResult(**report)
    app_logger.bind(module="analysis_router").info(
        f"growth report success knowledge_base_id={knowledge_base_id} "
        f"current_user_id={current_user.id} entry_count={len(entries)} recent_days={recent_days}"
    )
    return success_response(data=data)


@router.get("/knowledge-bases/{knowledge_base_id}/analytics")
async def get_knowledge_base_analytics(
        knowledge_base_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="analysis_router").info(
        f"analytics report request knowledge_base_id={knowledge_base_id} current_user_id={current_user.id}"
    )
    report = await build_knowledge_base_analytics_report(
        db,
        user_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
    )
    app_logger.bind(module="analysis_router").info(
        f"analytics report success knowledge_base_id={knowledge_base_id} "
        f"current_user_id={current_user.id} document_count={report.documents.document_count} "
        f"outbox_event_count={report.outbox.event_count}"
    )
    return success_response(
        data=KnowledgeBaseAnalyticsReportData.model_validate(report),
        message="analytics report built",
    )
