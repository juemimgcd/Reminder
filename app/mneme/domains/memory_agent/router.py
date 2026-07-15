from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.clients.memory_agent_client import MemoryAgentClient
from app.mneme.conf.database import get_database, get_write_database
from app.mneme.domains.memory_agent import service
from app.mneme.models.user import User
from app.mneme.schemas.memory_agent import (
    CandidateActionRequest,
    ConversationMemorySettingsUpdate,
    MemoryActionRequest,
    MemoryConfirmationRequest,
    MemoryPurgeRequest,
    MemoryRevisionRequest,
)
from app.mneme.utils.auth import get_current_user
from app.mneme.utils.exceptions import BusinessException
from app.mneme.utils.response import success_response

router = APIRouter(prefix="/api/v1/memory-agent", tags=["memory-agent"])


@router.get("/memories")
async def get_memories(
    knowledge_base_id: str | None = Query(default=None, max_length=64),
    status: str | None = Query(default="active", max_length=16),
    memory_type: str | None = Query(default=None, max_length=32),
    source_id: str | None = Query(default=None, max_length=128),
    cursor: str | None = Query(default=None, max_length=4096),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    await service.require_owned_knowledge_base(db, current_user=current_user, knowledge_base_id=knowledge_base_id)
    if source_id is not None:
        await service.require_owned_source(
            db, current_user=current_user, source_id=source_id, knowledge_base_id=knowledge_base_id
        )
    filters = {"status": status, "memory_type": memory_type, "source_id": source_id}
    data = await service.list_memories(
        owner_id=current_user.id, knowledge_base_id=knowledge_base_id, filters=filters, cursor=cursor, limit=limit
    )
    return success_response(data=data)


@router.get("/candidates")
async def get_candidates(
    knowledge_base_id: str | None = Query(default=None, max_length=64),
    status: str | None = Query(default="pending", max_length=16),
    memory_type: str | None = Query(default=None, max_length=32),
    source_id: str | None = Query(default=None, max_length=128),
    cursor: str | None = Query(default=None, max_length=4096),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    await service.require_owned_knowledge_base(db, current_user=current_user, knowledge_base_id=knowledge_base_id)
    if source_id is not None:
        await service.require_owned_source(
            db, current_user=current_user, source_id=source_id, knowledge_base_id=knowledge_base_id
        )
    filters = {"status": status, "memory_type": memory_type, "source_id": source_id}
    data = await service.list_candidates(
        owner_id=current_user.id, knowledge_base_id=knowledge_base_id, filters=filters, cursor=cursor, limit=limit
    )
    return success_response(data=data)


@router.get("/memories/{memory_id}")
async def get_memory_detail(
    memory_id: str,
    knowledge_base_id: str | None = Query(default=None, max_length=64),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    await _scope(db, current_user, knowledge_base_id)
    async with MemoryAgentClient() as client:
        data = await client.get_memory_detail(
            memory_id=memory_id, owner_id=current_user.id, knowledge_base_id=knowledge_base_id
        )
    return success_response(data=data)


@router.post("/confirmations")
async def create_confirmation(
    payload: MemoryConfirmationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    await service.require_owned_knowledge_base(
        db, current_user=current_user, knowledge_base_id=payload.knowledge_base_id
    )
    target_id = str(current_user.id) if payload.action == "purge_account" else payload.target_id or ""
    if payload.action == "purge_source":
        await service.require_owned_source(
            db, current_user=current_user, source_id=target_id, knowledge_base_id=payload.knowledge_base_id
        )
    if payload.action == "purge_knowledge_base" and target_id != payload.knowledge_base_id:
        raise BusinessException(message="confirmation target scope mismatch", code=4007, status_code=400)
    data = service.issue_confirmation(
        owner_id=current_user.id,
        knowledge_base_id=payload.knowledge_base_id,
        action=payload.action,
        target_id=target_id,
    )
    return success_response(data=data, message="confirmation issued")


async def _scope(db: AsyncSession, current_user: User, knowledge_base_id: str | None) -> None:
    await service.require_owned_knowledge_base(db, current_user=current_user, knowledge_base_id=knowledge_base_id)


@router.post("/candidates/{candidate_id}/confirm")
async def confirm_candidate(
    candidate_id: str,
    payload: CandidateActionRequest,
    knowledge_base_id: str | None = Query(default=None, max_length=64),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    await _scope(db, current_user, knowledge_base_id)
    service.verify_confirmation(
        payload.confirmation_token,
        owner_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        action="confirm_candidate",
        target_id=candidate_id,
    )
    async with MemoryAgentClient() as client:
        data = await client.command_candidate(
            candidate_id=candidate_id,
            owner_id=current_user.id,
            knowledge_base_id=knowledge_base_id,
            action="confirm",
            actor_id=f"user:{current_user.id}",
            reason=payload.reason,
        )
    return success_response(data=data)


@router.post("/candidates/{candidate_id}/reject")
async def reject_candidate(
    candidate_id: str,
    payload: CandidateActionRequest,
    knowledge_base_id: str | None = Query(default=None, max_length=64),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    await _scope(db, current_user, knowledge_base_id)
    service.verify_confirmation(
        payload.confirmation_token,
        owner_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        action="reject_candidate",
        target_id=candidate_id,
    )
    async with MemoryAgentClient() as client:
        data = await client.command_candidate(
            candidate_id=candidate_id,
            owner_id=current_user.id,
            knowledge_base_id=knowledge_base_id,
            action="reject",
            actor_id=f"user:{current_user.id}",
            reason=payload.reason,
        )
    return success_response(data=data)


@router.post("/memories/{memory_id}/revise")
async def revise_memory(
    memory_id: str,
    payload: MemoryRevisionRequest,
    knowledge_base_id: str | None = Query(default=None, max_length=64),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    await _scope(db, current_user, knowledge_base_id)
    service.verify_confirmation(
        payload.confirmation_token,
        owner_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        action="revise_memory",
        target_id=memory_id,
    )
    revision = payload.model_dump(exclude={"reason", "confirmation_token"})
    async with MemoryAgentClient() as client:
        data = await client.command_memory(
            memory_id=memory_id,
            owner_id=current_user.id,
            knowledge_base_id=knowledge_base_id,
            action="revise",
            actor_id=f"user:{current_user.id}",
            reason=payload.reason,
            revision=revision,
        )
    return success_response(data=data)


@router.post("/memories/{memory_id}/invalidate")
async def invalidate_memory(
    memory_id: str,
    payload: MemoryActionRequest,
    knowledge_base_id: str | None = Query(default=None, max_length=64),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    await _scope(db, current_user, knowledge_base_id)
    service.verify_confirmation(
        payload.confirmation_token,
        owner_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        action="invalidate_memory",
        target_id=memory_id,
    )
    async with MemoryAgentClient() as client:
        data = await client.command_memory(
            memory_id=memory_id,
            owner_id=current_user.id,
            knowledge_base_id=knowledge_base_id,
            action="invalidate",
            actor_id=f"user:{current_user.id}",
            reason=payload.reason,
        )
    return success_response(data=data)


@router.delete("/memories/{memory_id}")
async def hard_delete_memory(
    memory_id: str,
    payload: MemoryActionRequest,
    knowledge_base_id: str | None = Query(default=None, max_length=64),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    await _scope(db, current_user, knowledge_base_id)
    service.verify_confirmation(
        payload.confirmation_token,
        owner_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        action="hard_delete_memory",
        target_id=memory_id,
    )
    async with MemoryAgentClient() as client:
        data = await client.delete_memory(
            memory_id=memory_id,
            owner_id=current_user.id,
            knowledge_base_id=knowledge_base_id,
            actor_id=f"user:{current_user.id}",
            reason=payload.reason,
        )
    return success_response(data=data)


@router.post("/purge")
async def purge(
    payload: MemoryPurgeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    action = (
        "purge_source"
        if payload.source_id
        else "purge_knowledge_base"
        if payload.knowledge_base_id
        else "purge_account"
    )
    knowledge_base_id = payload.scope_knowledge_base_id if payload.source_id else payload.knowledge_base_id
    if payload.source_id is not None:
        await service.require_owned_source(
            db, current_user=current_user, source_id=payload.source_id, knowledge_base_id=knowledge_base_id
        )
    await service.require_owned_knowledge_base(db, current_user=current_user, knowledge_base_id=knowledge_base_id)
    target_id = payload.source_id or payload.knowledge_base_id or str(current_user.id)
    service.verify_confirmation(
        payload.confirmation_token,
        owner_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        action=action,
        target_id=target_id,
    )
    command = {
        "actor_id": f"user:{current_user.id}",
        "reason": payload.reason,
        "confirmation_token": payload.confirmation_token,
    }
    if payload.source_id is not None:
        command["source_id"] = payload.source_id
    elif payload.knowledge_base_id is not None:
        command["knowledge_base_id"] = payload.knowledge_base_id
    else:
        command["owner_id"] = current_user.id
    async with MemoryAgentClient() as client:
        data = await client.purge_memories(
            owner_id=current_user.id, knowledge_base_id=knowledge_base_id, payload=command
        )
    return success_response(data=data)


@router.get("/settings")
async def get_settings(current_user: User = Depends(get_current_user)):
    async with MemoryAgentClient() as client:
        data = await client.get_memory_settings(owner_id=current_user.id)
    return success_response(data=data)


@router.patch("/settings")
async def patch_settings(
    payload: ConversationMemorySettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    data = await service.update_settings(db, owner_id=current_user.id, enabled=payload.automatic_conversation_memory)
    return success_response(data=data, message="memory settings accepted")
