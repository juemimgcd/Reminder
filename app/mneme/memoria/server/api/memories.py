from datetime import datetime
from typing import Annotated, Any, Literal

import jwt
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, or_, select

from app.mneme.memoria.server.api.dependencies import require_claimed_scope, require_service_scope
from app.mneme.memoria.server.api.errors import AgentAPIError
from app.mneme.memoria.server.config import settings
from app.mneme.memoria.server.database import open_read_session, open_write_session
from app.mneme.memoria.server.memory.sensitivity import classify_sensitivity
from app.mneme.memoria.server.models.canonical_memory import CanonicalMemory
from app.mneme.memoria.server.models.evidence import Evidence, candidate_evidence, revision_evidence
from app.mneme.memoria.server.models.memory_candidate import MemoryCandidate
from app.mneme.memoria.server.models.memory_revision import MemoryRevision
from app.mneme.memoria.server.models.memory_settings import MemorySettings
from app.mneme.memoria.server.security.service_tokens import (
    MEMORIES_READ_SCOPE,
    MEMORIES_WRITE_SCOPE,
    SERVICE_TOKEN_ALGORITHM,
    SERVICE_TOKEN_ISSUER,
)
from app.mneme.memoria.server.services import memory_commands

router = APIRouter()


class CanonicalMemoryDTO(BaseModel):
    memory_id: str
    owner_id: int
    knowledge_base_id: str | None
    memory_type: str
    subject: str
    predicate: str
    value: str
    confidence: float
    status: str
    active_revision_id: str
    created_at: datetime
    updated_at: datetime


class CandidateDTO(BaseModel):
    candidate_id: str
    owner_id: int
    knowledge_base_id: str | None
    memory_type: str
    subject: str
    predicate: str
    value: str
    confidence: float
    status: str
    created_at: datetime
    decided_at: datetime | None


class MemoryList(BaseModel):
    items: list[CanonicalMemoryDTO]
    offset: int
    limit: int
    total: int


class CandidateList(BaseModel):
    items: list[CandidateDTO]
    offset: int
    limit: int
    total: int


class RevisionDTO(BaseModel):
    revision_id: str
    subject: str
    predicate: str
    value: str
    valid_from: datetime
    valid_to: datetime | None
    reason: str


class EvidenceDTO(BaseModel):
    evidence_id: str
    revision_id: str
    source_type: str
    source_id: str
    source_document_id: str | None
    excerpt: str
    source_time: datetime


class MemoryDetailDTO(BaseModel):
    memory: CanonicalMemoryDTO
    revisions: list[RevisionDTO]
    evidence: list[EvidenceDTO]


class CandidateCommand(BaseModel):
    owner_id: int = Field(gt=0)
    knowledge_base_id: str | None = Field(default=None, max_length=128)
    action: Literal["confirm", "reject"]
    actor_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=256)


class MemoryCommand(BaseModel):
    owner_id: int = Field(gt=0)
    knowledge_base_id: str | None = Field(default=None, max_length=128)
    action: Literal["revise", "invalidate"]
    actor_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=256)
    subject: str | None = Field(default=None, max_length=2000)
    predicate: str | None = Field(default=None, max_length=2000)
    value: str | None = Field(default=None, max_length=10000)
    confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def require_revision_fields(self) -> "MemoryCommand":
        if self.action == "revise" and any(value is None for value in (self.subject, self.predicate, self.value)):
            raise ValueError("revision fields are required")
        return self


class DeleteCommand(BaseModel):
    owner_id: int = Field(gt=0)
    knowledge_base_id: str | None = Field(default=None, max_length=128)
    actor_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=256)


class PurgeCommand(BaseModel):
    source_id: str | None = Field(default=None, min_length=1, max_length=128)
    knowledge_base_id: str | None = Field(default=None, min_length=1, max_length=128)
    owner_id: int | None = Field(default=None, gt=0)
    actor_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=256)
    confirmation_token: str = Field(min_length=1, max_length=4096)

    @model_validator(mode="after")
    def exactly_one_selector(self) -> "PurgeCommand":
        if sum(value is not None for value in (self.source_id, self.knowledge_base_id, self.owner_id)) != 1:
            raise ValueError("exactly one purge selector is required")
        return self


def _canonical(row: CanonicalMemory) -> CanonicalMemoryDTO:
    return CanonicalMemoryDTO.model_validate(row, from_attributes=True)


def _candidate(row: MemoryCandidate) -> CandidateDTO:
    return CandidateDTO.model_validate(row, from_attributes=True)


def _scope(column, knowledge_base_id: str | None):
    return column.is_(None) if knowledge_base_id is None else column == knowledge_base_id


@router.get("/memories", response_model=MemoryList)
async def list_memories(
    claims: Annotated[dict[str, Any], Depends(require_service_scope(MEMORIES_READ_SCOPE))],
    owner_id: int = Query(gt=0),
    knowledge_base_id: str | None = Query(default=None, max_length=128),
    status: str | None = Query(default="active", max_length=16),
    memory_type: str | None = Query(default=None, max_length=32),
    source_id: str | None = Query(default=None, max_length=128),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> MemoryList:
    require_claimed_scope(claims, owner_id=owner_id, knowledge_base_id=knowledge_base_id)
    query = select(CanonicalMemory).where(
        CanonicalMemory.owner_id == owner_id,
        _scope(CanonicalMemory.knowledge_base_id, knowledge_base_id),
    )
    if status is not None:
        query = query.where(CanonicalMemory.status == status)
    if memory_type is not None:
        query = query.where(CanonicalMemory.memory_type == memory_type)
    if source_id is not None:
        query = query.where(
            select(revision_evidence.c.revision_id)
            .join(Evidence, Evidence.evidence_id == revision_evidence.c.evidence_id)
            .join(MemoryRevision, MemoryRevision.revision_id == revision_evidence.c.revision_id)
            .where(
                MemoryRevision.memory_id == CanonicalMemory.memory_id,
                or_(Evidence.source_id == source_id, Evidence.source_document_id == source_id),
            )
            .exists()
        )
    query = query.order_by(CanonicalMemory.updated_at.desc(), CanonicalMemory.memory_id).offset(offset).limit(limit)
    count_query = select(func.count()).select_from(query.order_by(None).limit(None).offset(None).subquery())
    async with open_read_session() as db:
        total = int(await db.scalar(count_query) or 0)
        rows = list(await db.scalars(query))
    return MemoryList(items=[_canonical(row) for row in rows], offset=offset, limit=limit, total=total)


@router.get("/memories/{memory_id}", response_model=MemoryDetailDTO)
async def get_memory_detail(
    memory_id: str,
    claims: Annotated[dict[str, Any], Depends(require_service_scope(MEMORIES_READ_SCOPE))],
    owner_id: int = Query(gt=0),
    knowledge_base_id: str | None = Query(default=None, max_length=128),
) -> MemoryDetailDTO:
    require_claimed_scope(claims, owner_id=owner_id, knowledge_base_id=knowledge_base_id)
    async with open_read_session() as db:
        memory = await db.scalar(
            select(CanonicalMemory).where(
                CanonicalMemory.memory_id == memory_id,
                CanonicalMemory.owner_id == owner_id,
                _scope(CanonicalMemory.knowledge_base_id, knowledge_base_id),
            )
        )
        if memory is None:
            raise AgentAPIError(status_code=404, code="MEMORY_NOT_FOUND")
        revisions = list(
            await db.scalars(
                select(MemoryRevision)
                .where(MemoryRevision.memory_id == memory_id)
                .order_by(MemoryRevision.valid_from.desc(), MemoryRevision.revision_id)
            )
        )
        evidence_rows = list(
            (
                await db.execute(
                    select(MemoryRevision.revision_id, Evidence)
                    .join(revision_evidence, revision_evidence.c.revision_id == MemoryRevision.revision_id)
                    .join(Evidence, Evidence.evidence_id == revision_evidence.c.evidence_id)
                    .where(
                        MemoryRevision.memory_id == memory_id,
                        Evidence.owner_id == owner_id,
                        _scope(Evidence.knowledge_base_id, knowledge_base_id),
                    )
                    .order_by(Evidence.occurred_at.desc(), Evidence.evidence_id)
                )
            ).all()
        )
    return MemoryDetailDTO(
        memory=_canonical(memory),
        revisions=[RevisionDTO.model_validate(row, from_attributes=True) for row in revisions],
        evidence=[
            EvidenceDTO(
                evidence_id=evidence.evidence_id,
                revision_id=revision_id,
                source_type=evidence.source_type,
                source_id=evidence.source_id,
                source_document_id=evidence.source_document_id,
                excerpt=evidence.minimum_text,
                source_time=evidence.occurred_at,
            )
            for revision_id, evidence in evidence_rows
        ],
    )


@router.get("/memory-candidates", response_model=CandidateList)
async def list_candidates(
    claims: Annotated[dict[str, Any], Depends(require_service_scope(MEMORIES_READ_SCOPE))],
    owner_id: int = Query(gt=0),
    knowledge_base_id: str | None = Query(default=None, max_length=128),
    status: str | None = Query(default="pending", max_length=16),
    memory_type: str | None = Query(default=None, max_length=32),
    source_id: str | None = Query(default=None, max_length=128),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> CandidateList:
    require_claimed_scope(claims, owner_id=owner_id, knowledge_base_id=knowledge_base_id)
    query = select(MemoryCandidate).where(
        MemoryCandidate.owner_id == owner_id,
        _scope(MemoryCandidate.knowledge_base_id, knowledge_base_id),
    )
    if status is not None:
        query = query.where(MemoryCandidate.status == status)
    if memory_type is not None:
        query = query.where(MemoryCandidate.memory_type == memory_type)
    if source_id is not None:
        query = query.where(
            select(candidate_evidence.c.candidate_id)
            .join(Evidence, Evidence.evidence_id == candidate_evidence.c.evidence_id)
            .where(
                candidate_evidence.c.candidate_id == MemoryCandidate.candidate_id,
                or_(Evidence.source_id == source_id, Evidence.source_document_id == source_id),
            )
            .exists()
        )
    query = query.order_by(MemoryCandidate.created_at.desc(), MemoryCandidate.candidate_id).offset(offset).limit(limit)
    count_query = select(func.count()).select_from(query.order_by(None).limit(None).offset(None).subquery())
    async with open_read_session() as db:
        total = int(await db.scalar(count_query) or 0)
        rows = list(await db.scalars(query))
    return CandidateList(items=[_candidate(row) for row in rows], offset=offset, limit=limit, total=total)


@router.get("/memory-settings")
async def get_memory_settings(
    claims: Annotated[dict[str, Any], Depends(require_service_scope(MEMORIES_READ_SCOPE))],
    owner_id: int = Query(gt=0),
) -> dict[str, bool]:
    require_claimed_scope(claims, owner_id=owner_id, knowledge_base_id=None)
    async with open_read_session() as db:
        row = await db.get(MemorySettings, owner_id)
    return {
        "automatic_conversation_memory": bool(row and row.automatic_conversation_memory),
        "applied": row is not None,
    }


@router.patch("/memory-candidates/{candidate_id}")
async def command_candidate(
    candidate_id: str,
    command: CandidateCommand,
    claims: Annotated[dict[str, Any], Depends(require_service_scope(MEMORIES_WRITE_SCOPE))],
) -> CanonicalMemoryDTO | CandidateDTO:
    require_claimed_scope(claims, owner_id=command.owner_id, knowledge_base_id=command.knowledge_base_id)
    try:
        async with open_write_session() as db:
            if command.action == "confirm":
                return _canonical(
                    await memory_commands.confirm(
                        db,
                        candidate_id=candidate_id,
                        owner_id=command.owner_id,
                        knowledge_base_id=command.knowledge_base_id,
                        actor_id=command.actor_id,
                        reason=command.reason,
                    )
                )
            return _candidate(
                await memory_commands.reject(
                    db,
                    candidate_id=candidate_id,
                    owner_id=command.owner_id,
                    knowledge_base_id=command.knowledge_base_id,
                    actor_id=command.actor_id,
                    reason=command.reason,
                )
            )
    except LookupError:
        raise AgentAPIError(status_code=404, code="MEMORY_NOT_FOUND") from None
    except ValueError:
        raise AgentAPIError(status_code=409, code="MEMORY_COMMAND_REJECTED") from None


@router.patch("/memories/{memory_id}", response_model=CanonicalMemoryDTO)
async def command_memory(
    memory_id: str,
    command: MemoryCommand,
    claims: Annotated[dict[str, Any], Depends(require_service_scope(MEMORIES_WRITE_SCOPE))],
) -> CanonicalMemoryDTO:
    require_claimed_scope(claims, owner_id=command.owner_id, knowledge_base_id=command.knowledge_base_id)
    try:
        async with open_write_session() as db:
            if command.action == "invalidate":
                row = await memory_commands.invalidate(
                    db,
                    memory_id=memory_id,
                    owner_id=command.owner_id,
                    knowledge_base_id=command.knowledge_base_id,
                    actor_id=command.actor_id,
                    reason=command.reason,
                )
            else:
                assert command.subject is not None and command.predicate is not None and command.value is not None
                if classify_sensitivity(command.subject, command.predicate, command.value) == "secret":
                    raise ValueError("secret values cannot be persisted")
                row = await memory_commands.revise(
                    db,
                    memory_id=memory_id,
                    owner_id=command.owner_id,
                    knowledge_base_id=command.knowledge_base_id,
                    subject=command.subject,
                    predicate=command.predicate,
                    value=command.value,
                    confidence=command.confidence,
                    actor_id=command.actor_id,
                    reason=command.reason,
                )
            return _canonical(row)
    except LookupError:
        raise AgentAPIError(status_code=404, code="MEMORY_NOT_FOUND") from None
    except ValueError:
        raise AgentAPIError(status_code=409, code="MEMORY_COMMAND_REJECTED") from None


@router.delete("/memories/{memory_id}")
async def delete_memory(
    memory_id: str,
    command: DeleteCommand,
    claims: Annotated[dict[str, Any], Depends(require_service_scope(MEMORIES_WRITE_SCOPE))],
) -> dict[str, bool | str]:
    require_claimed_scope(claims, owner_id=command.owner_id, knowledge_base_id=command.knowledge_base_id)
    try:
        async with open_write_session() as db:
            await memory_commands.hard_delete(
                db,
                memory_id=memory_id,
                owner_id=command.owner_id,
                knowledge_base_id=command.knowledge_base_id,
                actor_id=command.actor_id,
                reason=command.reason,
            )
    except LookupError:
        raise AgentAPIError(status_code=404, code="MEMORY_NOT_FOUND") from None
    return {"memory_id": memory_id, "deleted": True}


def _validate_confirmation(
    command: PurgeCommand,
    *,
    owner_id: int,
    knowledge_base_id: str | None,
) -> str:
    try:
        claims = jwt.decode(
            command.confirmation_token,
            settings.SERVICE_JWT_SECRET.get_secret_value(),
            algorithms=[SERVICE_TOKEN_ALGORITHM],
            audience="memory-agent-purge",
            issuer=SERVICE_TOKEN_ISSUER,
            options={
                "require": [
                    "iss",
                    "aud",
                    "iat",
                    "exp",
                    "jti",
                    "purpose",
                    "owner_id",
                    "knowledge_base_id",
                    "selector_type",
                    "selector_value",
                ]
            },
        )
    except jwt.PyJWTError:
        raise AgentAPIError(status_code=403, code="PURGE_CONFIRMATION_INVALID") from None
    selector_type = (
        "source_id"
        if command.source_id is not None
        else "knowledge_base_id"
        if command.knowledge_base_id is not None
        else "owner_id"
    )
    selector_value: str | int = command.source_id or command.knowledge_base_id or command.owner_id or ""
    if (
        claims.get("purpose") != "memory-purge"
        or claims.get("owner_id") != owner_id
        or claims.get("knowledge_base_id") != knowledge_base_id
        or claims.get("selector_type") != selector_type
        or claims.get("selector_value") != selector_value
    ):
        raise AgentAPIError(status_code=403, code="PURGE_CONFIRMATION_INVALID")
    confirmation_jti = claims.get("jti")
    if not isinstance(confirmation_jti, str) or not 1 <= len(confirmation_jti) <= 128:
        raise AgentAPIError(status_code=403, code="PURGE_CONFIRMATION_INVALID")
    return confirmation_jti


@router.post("/memories/purge")
async def purge_memories(
    command: PurgeCommand,
    claims: Annotated[dict[str, Any], Depends(require_service_scope(MEMORIES_WRITE_SCOPE))],
) -> dict[str, int | bool]:
    owner_id = claims["owner_id"]
    token_kb = claims["knowledge_base_id"]
    require_claimed_scope(claims, owner_id=owner_id, knowledge_base_id=token_kb)
    if command.owner_id is not None:
        if command.owner_id != owner_id or token_kb is not None:
            raise AgentAPIError(status_code=403, code="AGENT_SCOPE_MISMATCH")
    elif command.knowledge_base_id is not None:
        if command.knowledge_base_id != token_kb:
            raise AgentAPIError(status_code=403, code="AGENT_SCOPE_MISMATCH")
    confirmation_jti = _validate_confirmation(
        command,
        owner_id=owner_id,
        knowledge_base_id=token_kb,
    )
    target = command.source_id or command.knowledge_base_id or str(owner_id)
    try:
        async with open_write_session() as db:
            await memory_commands.consume_purge_confirmation(
                db,
                owner_id=owner_id,
                knowledge_base_id=token_kb,
                target_id=target,
                actor_id=command.actor_id,
                reason=command.reason,
                confirmation_jti=confirmation_jti,
            )
            if command.source_id is not None:
                counts = await memory_commands.purge_source(
                    db,
                    owner_id=owner_id,
                    knowledge_base_id=token_kb,
                    source_id=command.source_id,
                )
            elif command.knowledge_base_id is not None:
                counts = await memory_commands.purge_knowledge_base(
                    db,
                    owner_id=owner_id,
                    knowledge_base_id=command.knowledge_base_id,
                )
            else:
                counts = await memory_commands.purge_owner(db, owner_id=owner_id)
    except memory_commands.PurgeConfirmationReplay:
        raise AgentAPIError(status_code=403, code="PURGE_CONFIRMATION_INVALID") from None
    return {
        "purged": True,
        "deleted_evidence_count": counts.evidence,
        "deleted_candidate_count": counts.candidates,
        "deleted_revision_count": counts.revisions,
        "deleted_memory_count": counts.memories,
    }
