import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.memoria.server.contracts.events import AgentEventEnvelope
from app.mneme.memoria.server.database import open_read_session
from app.mneme.memoria.server.models.source_deletion_fence import SourceDeletionFence

FenceSourceType = Literal[
    "knowledge_base",
    "document",
    "conversation",
    "explicit_request",
]


@dataclass(frozen=True)
class FenceSource:
    source_type: FenceSourceType
    source_id: str


def _fence_key(
    *,
    owner_id: int,
    knowledge_base_id: str | None,
    source: FenceSource,
) -> str:
    serialized = json.dumps(
        [
            "mneme:source-deletion-fence",
            1,
            owner_id,
            knowledge_base_id,
            source.source_type,
            source.source_id,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _order(occurred_at: datetime, event_id: str) -> tuple[datetime, str]:
    return occurred_at, event_id


def _sources_with_knowledge_base(
    event: AgentEventEnvelope,
    sources: list[FenceSource],
) -> list[FenceSource]:
    scoped = list(sources)
    if event.knowledge_base_id is not None:
        scoped.append(
            FenceSource(
                source_type="knowledge_base",
                source_id=event.knowledge_base_id,
            )
        )
    return list(dict.fromkeys(scoped))


async def event_is_blocked_by_deletion(
    event: AgentEventEnvelope,
    *,
    sources: list[FenceSource],
) -> bool:
    scoped_sources = _sources_with_knowledge_base(event, sources)
    if not scoped_sources:
        return False
    keys = {
        _fence_key(
            owner_id=event.owner_id,
            knowledge_base_id=event.knowledge_base_id,
            source=source,
        )
        for source in scoped_sources
    }
    fences = []
    ordered_keys = sorted(keys)
    async with open_read_session() as db:
        for offset in range(0, len(ordered_keys), 1_000):
            fences.extend(
                await db.scalars(
                    select(SourceDeletionFence).where(
                        SourceDeletionFence.fence_key.in_(
                            ordered_keys[offset : offset + 1_000]
                        )
                    )
                )
            )
    event_order = _order(event.occurred_at, event.event_id)
    return any(
        _order(fence.deleted_at, fence.delete_event_id) >= event_order
        for fence in fences
    )


async def advance_deletion_fences(
    db: AsyncSession,
    *,
    event: AgentEventEnvelope,
    primary: FenceSource,
    additional: list[FenceSource] | None = None,
) -> bool:
    primary_key = _fence_key(
        owner_id=event.owner_id,
        knowledge_base_id=event.knowledge_base_id,
        source=primary,
    )
    current = await db.scalar(
        select(SourceDeletionFence)
        .where(SourceDeletionFence.fence_key == primary_key)
        .with_for_update()
    )
    incoming_order = _order(event.occurred_at, event.event_id)
    if (
        current is not None
        and _order(current.deleted_at, current.delete_event_id) >= incoming_order
    ):
        return False

    sources = list(dict.fromkeys([primary, *(additional or [])]))
    values = [
        {
            "fence_key": _fence_key(
                owner_id=event.owner_id,
                knowledge_base_id=event.knowledge_base_id,
                source=source,
            ),
            "owner_id": event.owner_id,
            "knowledge_base_id": event.knowledge_base_id,
            "source_type": source.source_type,
            "source_id": source.source_id,
            "deleted_at": event.occurred_at,
            "delete_event_id": event.event_id,
        }
        for source in sources
    ]
    for offset in range(0, len(values), 1_000):
        statement = insert(SourceDeletionFence).values(values[offset : offset + 1_000])
        excluded = statement.excluded
        await db.execute(
            statement.on_conflict_do_update(
                index_elements=[SourceDeletionFence.fence_key],
                set_={
                    "deleted_at": excluded.deleted_at,
                    "delete_event_id": excluded.delete_event_id,
                    "updated_at": func.now(),
                },
                where=or_(
                    excluded.deleted_at > SourceDeletionFence.deleted_at,
                    and_(
                        excluded.deleted_at == SourceDeletionFence.deleted_at,
                        excluded.delete_event_id > SourceDeletionFence.delete_event_id,
                    ),
                ),
            )
        )
    return True
