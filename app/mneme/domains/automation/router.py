import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.agent.actions import WRITE_ACTION_CATALOG
from app.mneme.conf.database import get_database, get_write_database
from app.mneme.crud.agent_automation import (
    create_or_get_tool_approval,
    get_heartbeat_job,
    get_tool_approval,
    list_heartbeat_jobs,
    list_notifications,
    list_tool_approvals,
    count_unread_notifications,
    mark_notification_read,
)
from app.mneme.domains.automation.service import create_user_heartbeat_job, dispatch_heartbeat_job
from app.mneme.domains.chat.service import require_owned_knowledge_base
from app.mneme.models.user import User
from app.mneme.schemas.agent_automation import (
    HeartbeatJobCreateRequest,
    HeartbeatJobData,
    HeartbeatJobUpdateRequest,
    NotificationData,
    NotificationListData,
    ToolApprovalCreateRequest,
    ToolApprovalData,
    ToolApprovalDecisionRequest,
)
from app.mneme.utils.auth import get_current_user
from app.mneme.utils.exceptions import BusinessException
from app.mneme.utils.response import success_response

router = APIRouter(prefix="/agent", tags=["agent-automation"])


@router.get("/heartbeats")
async def get_heartbeat_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    rows = await list_heartbeat_jobs(db, user_id=current_user.id)
    return success_response(data=[HeartbeatJobData.model_validate(row) for row in rows])


@router.post("/heartbeats")
async def create_heartbeat(
    payload: HeartbeatJobCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    if payload.answer_mode != "general_chat" and not payload.knowledge_base_id:
        raise BusinessException(message="knowledge base is required for this answer mode", code=4053)
    if payload.knowledge_base_id:
        await require_owned_knowledge_base(
            db,
            current_user=current_user,
            knowledge_base_id=payload.knowledge_base_id,
        )
    job = await create_user_heartbeat_job(db, user_id=current_user.id, payload=payload)
    return success_response(data=HeartbeatJobData.model_validate(job), message="heartbeat created")


@router.patch("/heartbeats/{job_id}")
async def update_heartbeat(
    job_id: str,
    payload: HeartbeatJobUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    job = await get_heartbeat_job(db, job_id=job_id, user_id=current_user.id)
    if job is None:
        raise BusinessException(message="heartbeat job not found", code=4054, status_code=404)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(job, field, value)
    await db.flush()
    await db.refresh(job)
    return success_response(data=HeartbeatJobData.model_validate(job), message="heartbeat updated")


@router.post("/heartbeats/{job_id}/run")
async def run_heartbeat_now(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    job = await get_heartbeat_job(db, job_id=job_id, user_id=current_user.id)
    if job is None:
        raise BusinessException(message="heartbeat job not found", code=4054, status_code=404)
    run = await dispatch_heartbeat_job(
        db,
        job=job,
        occurrence_key=f"manual:{uuid.uuid4().hex}",
        force=True,
    )
    return success_response(data=run, message="heartbeat queued")


@router.get("/notifications")
async def get_notifications(
    limit: int = Query(default=30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    rows = await list_notifications(db, user_id=current_user.id, limit=limit)
    unread = await count_unread_notifications(db, user_id=current_user.id)
    return success_response(
        data=NotificationListData(
            items=[NotificationData.model_validate(row) for row in rows],
            unread_count=unread,
        )
    )


@router.post("/notifications/{notification_id}/read")
async def read_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    row = await mark_notification_read(db, notification_id=notification_id, user_id=current_user.id)
    if row is None:
        raise BusinessException(message="notification not found", code=4055, status_code=404)
    return success_response(data=NotificationData.model_validate(row))


@router.get("/approvals")
async def get_approvals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    rows = await list_tool_approvals(db, user_id=current_user.id)
    return success_response(data=[ToolApprovalData.model_validate(row) for row in rows])


@router.post("/approvals")
async def propose_action(
    payload: ToolApprovalCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    definition = WRITE_ACTION_CATALOG.get(payload.action_name)
    if definition is None:
        raise BusinessException(message="unknown write action", code=4056, status_code=400)
    approval = await create_or_get_tool_approval(
        db,
        id=f"approval_{uuid.uuid4().hex}",
        user_id=current_user.id,
        run_id=payload.run_id,
        action_name=definition.name,
        risk_level=definition.risk_level.value,
        action_summary=payload.action_summary,
        arguments_json=payload.arguments,
        status="pending",
        apply_enabled=definition.apply_enabled,
        idempotency_key=f"{current_user.id}:{payload.idempotency_key}",
    )
    return success_response(data=ToolApprovalData.model_validate(approval), message="action proposed")


@router.post("/approvals/{approval_id}/decision")
async def decide_action(
    approval_id: str,
    payload: ToolApprovalDecisionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    approval = await get_tool_approval(db, approval_id=approval_id, user_id=current_user.id)
    if approval is None:
        raise BusinessException(message="approval not found", code=4057, status_code=404)
    if approval.status != "pending":
        return success_response(data=ToolApprovalData.model_validate(approval), message="decision already recorded")
    approval.status = payload.decision
    approval.decision_reason = payload.reason
    approval.decided_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(approval)
    message = "proposal approved; apply remains disabled" if payload.decision == "approved" else "proposal rejected"
    return success_response(data=ToolApprovalData.model_validate(approval), message=message)
