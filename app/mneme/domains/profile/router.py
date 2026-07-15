import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.database import get_database, get_write_database
from app.mneme.conf.logging import app_logger
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id
from app.mneme.domains.automation.service import emit_domain_event
from app.mneme.domains.profile.insight import build_evidence_profile_for_knowledge_base, build_profile_for_knowledge_base
from app.mneme.models.user import User
from app.mneme.schemas.profile import PersonalProfileResult
from app.mneme.schemas.profile_evidence import EvidenceProfileData
from app.mneme.utils.auth import get_current_user
from app.mneme.utils.response import success_response


router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/knowledge-bases/{knowledge_base_id}")
async def get_personal_profile(
        knowledge_base_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_write_database),
):
    app_logger.bind(module="profile_router").info(
        f"profile request knowledge_base_id={knowledge_base_id} current_user_id={current_user.id}"
    )
    kb = await get_knowledge_base_by_id(db, knowledge_base_id=knowledge_base_id)
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="knowledge_base not found")

    if kb.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="you have no right")

    entries, result = await build_profile_for_knowledge_base(
        db,
        user_id=current_user.id,
        knowledge_base_id=kb.id,
    )
    data = PersonalProfileResult(**result)
    profile_hash = hashlib.sha256(
        json.dumps(data.model_dump(mode="json"), ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    await emit_domain_event(
        db,
        event_type="profile.updated",
        user_id=current_user.id,
        aggregate_type="knowledge_base",
        aggregate_id=kb.id,
        operation_id=profile_hash,
        payload={"knowledge_base_id": kb.id, "profile_hash": profile_hash},
    )
    app_logger.bind(module="profile_router").info(
        f"profile success knowledge_base_id={knowledge_base_id} current_user_id={current_user.id} "
        f"entry_count={len(entries)}"
    )

    return success_response(data=data)


@router.get("/knowledge-bases/{knowledge_base_id}/evidence")
async def get_evidence_profile(
        knowledge_base_id: str,
        recent_days: int = 30,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="profile_router").info(
        f"evidence profile request knowledge_base_id={knowledge_base_id} "
        f"current_user_id={current_user.id} recent_days={recent_days}"
    )

    kb = await get_knowledge_base_by_id(db, knowledge_base_id=knowledge_base_id)
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="knowledge_base not found")

    if kb.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="you have no right")

    entries, result = await build_evidence_profile_for_knowledge_base(
        db,
        knowledge_base_id=kb.id,
        recent_days=recent_days,
    )
    data = EvidenceProfileData(**result)
    app_logger.bind(module="profile_router").info(
        f"evidence profile success knowledge_base_id={knowledge_base_id} "
        f"current_user_id={current_user.id} entry_count={len(entries)}"
    )

    return success_response(data=data, message="evidence profile built")
