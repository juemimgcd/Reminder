import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.memoria.server.contracts.events import DocumentProjectionPayload
from app.mneme.memoria.server.models.document_projection import DocumentProjection
from app.mneme.memoria.server.models.projection_batch import DocumentProjectionBatch


@dataclass(frozen=True)
class StoredProjectionBatch:
    batch: DocumentProjectionBatch
    created: bool


class ProjectionIntegrityError(ValueError):
    """The projection payload is deterministically invalid and must not be retried."""


def projection_batch_payload_hash(payload: DocumentProjectionPayload) -> str:
    serialized = json.dumps(
        [chunk.model_dump(mode="json") for chunk in payload.chunks],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


async def store_projection_batch(
    db: AsyncSession,
    *,
    payload: DocumentProjectionPayload,
    owner_id: int,
    knowledge_base_id: str,
) -> StoredProjectionBatch:
    await db.execute(
        insert(DocumentProjection)
        .values(
            projection_id=payload.projection_id,
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            document_id=payload.document_id,
            document_version=payload.document_version,
            file_name=payload.file_name,
            batch_count=payload.batch_count,
            aggregate_hash=payload.aggregate_hash,
        )
        .on_conflict_do_nothing()
    )
    projection = await db.scalar(
        select(DocumentProjection)
        .where(DocumentProjection.projection_id == payload.projection_id)
        .with_for_update()
    )
    if projection is None:
        conflicting = await db.scalar(
            select(DocumentProjection).where(
                DocumentProjection.owner_id == owner_id,
                DocumentProjection.knowledge_base_id == knowledge_base_id,
                DocumentProjection.document_id == payload.document_id,
                DocumentProjection.document_version == payload.document_version,
            )
        )
        conflict_id = conflicting.projection_id if conflicting is not None else "unknown"
        raise ProjectionIntegrityError(
            "document version is already assigned to a different projection "
            f"({conflict_id})"
        )

    expected_metadata = (
        owner_id,
        knowledge_base_id,
        payload.document_id,
        payload.document_version,
        payload.file_name,
        payload.batch_count,
        payload.aggregate_hash,
    )
    stored_metadata = (
        projection.owner_id,
        projection.knowledge_base_id,
        projection.document_id,
        projection.document_version,
        projection.file_name,
        projection.batch_count,
        projection.aggregate_hash,
    )
    if stored_metadata != expected_metadata:
        raise ProjectionIntegrityError("projection metadata changed between batches")
    if projection.status == "failed":
        raise ProjectionIntegrityError("cannot replay a failed projection")

    payload_hash = projection_batch_payload_hash(payload)
    existing = await db.scalar(
        select(DocumentProjectionBatch).where(
            DocumentProjectionBatch.projection_id == payload.projection_id,
            DocumentProjectionBatch.batch_index == payload.batch_index,
        )
    )
    if existing is not None:
        if existing.payload_hash != payload_hash:
            raise ProjectionIntegrityError("projection batch payload changed on replay")
        return StoredProjectionBatch(batch=existing, created=False)
    if projection.status != "staging":
        raise ProjectionIntegrityError(
            f"cannot add a missing batch to a {projection.status} projection"
        )

    batch = DocumentProjectionBatch(
        projection_id=payload.projection_id,
        batch_index=payload.batch_index,
        payload_hash=payload_hash,
        chunks=[chunk.model_dump(mode="json") for chunk in payload.chunks],
    )
    db.add(batch)
    await db.flush()
    return StoredProjectionBatch(batch=batch, created=True)


async def load_projection_for_update(
    db: AsyncSession, projection_id: str
) -> DocumentProjection | None:
    return await db.scalar(
        select(DocumentProjection)
        .where(DocumentProjection.projection_id == projection_id)
        .with_for_update()
    )


async def load_projection_batches(
    db: AsyncSession, projection_id: str
) -> list[DocumentProjectionBatch]:
    return list(
        await db.scalars(
            select(DocumentProjectionBatch)
            .where(DocumentProjectionBatch.projection_id == projection_id)
            .order_by(DocumentProjectionBatch.batch_index)
        )
    )
