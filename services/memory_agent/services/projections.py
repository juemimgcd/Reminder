import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory_agent.contracts.events import (
    DocumentChunkPayload,
    DocumentProjectionPayload,
)
from services.memory_agent.database import engine, open_write_session
from services.memory_agent.models.document_chunk import DocumentChunk
from services.memory_agent.models.document_projection import DocumentProjection
from services.memory_agent.repositories.projections import (
    load_projection_batches,
    load_projection_for_update,
    store_projection_batch,
)
from services.memory_agent.services.embeddings import embed_texts


class ProjectionIntegrityError(ValueError):
    pass


class IncompleteProjectionError(ProjectionIntegrityError):
    pass


@dataclass(frozen=True)
class ProjectionBatchReceipt:
    projection_id: str
    batch_index: int
    created: bool
    is_final_batch: bool


@dataclass(frozen=True)
class PreparedProjection:
    projection_id: str
    owner_id: int
    knowledge_base_id: str | None
    document_id: str
    document_version: str
    chunks: tuple[DocumentChunkPayload, ...]
    snapshot_hash: str


def _validate_sha256(value: str, *, field: str) -> None:
    if len(value) != 64:
        raise ProjectionIntegrityError(f"{field} must be a SHA-256 hex digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ProjectionIntegrityError(f"{field} must be a SHA-256 hex digest") from exc
    if value != value.lower():
        raise ProjectionIntegrityError(f"{field} must use lowercase hexadecimal")


def _snapshot_hash(chunks: list[DocumentChunkPayload]) -> str:
    serialized = json.dumps(
        [chunk.model_dump(mode="json") for chunk in chunks],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


async def _prepare_projection(
    db: AsyncSession, projection: DocumentProjection
) -> PreparedProjection:
    batches = await load_projection_batches(db, projection.projection_id)
    received_indexes = [batch.batch_index for batch in batches]
    expected_indexes = list(range(projection.batch_count))
    if received_indexes != expected_indexes:
        raise IncompleteProjectionError(
            f"projection requires batch indexes {expected_indexes}; received {received_indexes}"
        )

    chunks = [
        DocumentChunkPayload.model_validate(raw_chunk)
        for batch in batches
        for raw_chunk in batch.chunks
    ]
    chunks.sort(key=lambda chunk: (chunk.chunk_index, chunk.chunk_id))
    chunk_indexes = [chunk.chunk_index for chunk in chunks]
    if chunk_indexes != list(range(len(chunks))):
        raise ProjectionIntegrityError("chunk indexes must be unique and contiguous from zero")
    chunk_ids = [chunk.chunk_id for chunk in chunks]
    if len(chunk_ids) != len(set(chunk_ids)):
        raise ProjectionIntegrityError("chunk IDs must be unique within a projection")

    for chunk in chunks:
        _validate_sha256(chunk.content_hash, field=f"chunk {chunk.chunk_id} content_hash")
        computed_hash = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
        if computed_hash != chunk.content_hash:
            raise ProjectionIntegrityError(f"content hash mismatch for chunk {chunk.chunk_id}")

    _validate_sha256(projection.aggregate_hash, field="aggregate_hash")
    computed_aggregate = hashlib.sha256(
        "".join(chunk.content_hash for chunk in chunks).encode("ascii")
    ).hexdigest()
    if computed_aggregate != projection.aggregate_hash:
        raise ProjectionIntegrityError("projection aggregate hash mismatch")

    return PreparedProjection(
        projection_id=projection.projection_id,
        owner_id=projection.owner_id,
        knowledge_base_id=projection.knowledge_base_id,
        document_id=projection.document_id,
        document_version=projection.document_version,
        chunks=tuple(chunks),
        snapshot_hash=_snapshot_hash(chunks),
    )


async def stage_projection_batch(
    payload: DocumentProjectionPayload,
    *,
    owner_id: int,
    knowledge_base_id: str | None,
) -> ProjectionBatchReceipt:
    if payload.batch_index >= payload.batch_count:
        raise ProjectionIntegrityError("batch_index must be less than batch_count")
    _validate_sha256(payload.aggregate_hash, field="aggregate_hash")
    for chunk in payload.chunks:
        _validate_sha256(chunk.content_hash, field=f"chunk {chunk.chunk_id} content_hash")
        if hashlib.sha256(chunk.content.encode("utf-8")).hexdigest() != chunk.content_hash:
            raise ProjectionIntegrityError(f"content hash mismatch for chunk {chunk.chunk_id}")

    async with open_write_session() as db:
        stored = await store_projection_batch(
            db,
            payload=payload,
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
        )
    return ProjectionBatchReceipt(
        projection_id=payload.projection_id,
        batch_index=payload.batch_index,
        created=stored.created,
        is_final_batch=payload.batch_index == payload.batch_count - 1,
    )


async def _mark_failed(db: AsyncSession, projection_id: str, reason: str) -> None:
    await db.rollback()
    async with db.begin():
        projection = await load_projection_for_update(db, projection_id)
        if projection is not None and projection.status == "staging":
            projection.status = "failed"
            projection.failure_reason = reason[:2000]


async def _activate_projection(
    db: AsyncSession,
    prepared: PreparedProjection,
    embeddings: list[list[float]],
) -> bool:
    projection = await load_projection_for_update(db, prepared.projection_id)
    if projection is None:
        raise LookupError(f"projection {prepared.projection_id} does not exist")
    if projection.status in {"active", "superseded"}:
        return False
    if projection.status != "staging":
        raise ProjectionIntegrityError(f"cannot finalize a {projection.status} projection")

    rechecked = await _prepare_projection(db, projection)
    if rechecked.snapshot_hash != prepared.snapshot_hash:
        raise ProjectionIntegrityError("projection batches changed during embedding")
    if len(embeddings) != len(rechecked.chunks):
        raise ProjectionIntegrityError("embedding count does not match chunk count")

    scope_filter: list[Any] = [
        DocumentProjection.owner_id == projection.owner_id,
        DocumentProjection.document_id == projection.document_id,
        DocumentProjection.status == "active",
        DocumentProjection.projection_id != projection.projection_id,
    ]
    if projection.knowledge_base_id is None:
        scope_filter.append(DocumentProjection.knowledge_base_id.is_(None))
    else:
        scope_filter.append(
            DocumentProjection.knowledge_base_id == projection.knowledge_base_id
        )
    old_projections = list(
        await db.scalars(select(DocumentProjection).where(*scope_filter).with_for_update())
    )
    old_projection_ids = [row.projection_id for row in old_projections]
    if old_projection_ids:
        await db.execute(
            update(DocumentChunk)
            .where(DocumentChunk.projection_id.in_(old_projection_ids))
            .values(is_active=False)
        )
        for old_projection in old_projections:
            old_projection.status = "superseded"

    db.add_all(
        [
            DocumentChunk(
                projection_id=projection.projection_id,
                owner_id=projection.owner_id,
                knowledge_base_id=projection.knowledge_base_id,
                document_id=projection.document_id,
                document_version=projection.document_version,
                chunk_id=chunk.chunk_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                content_hash=chunk.content_hash,
                page_no=chunk.page_no,
                section_path=chunk.section_path,
                embedding=embedding,
                is_active=False,
            )
            for chunk, embedding in zip(rechecked.chunks, embeddings, strict=True)
        ]
    )
    await db.flush()
    await db.execute(
        update(DocumentChunk)
        .where(DocumentChunk.projection_id == projection.projection_id)
        .values(is_active=True)
    )
    projection.status = "active"
    projection.failure_reason = None
    projection.activated_at = datetime.now(UTC)
    return True


async def finalize_projection(projection_id: str) -> bool:
    async with engine.connect() as connection:
        await connection.execute(
            text("SELECT pg_advisory_lock(hashtextextended(:projection_id, 0))"),
            {"projection_id": projection_id},
        )
        await connection.commit()
        try:
            async with AsyncSession(bind=connection, expire_on_commit=False) as db:
                projection = await db.get(DocumentProjection, projection_id)
                if projection is None:
                    raise LookupError(f"projection {projection_id} does not exist")
                if projection.status in {"active", "superseded"}:
                    await db.rollback()
                    return False
                if projection.status != "staging":
                    await db.rollback()
                    raise ProjectionIntegrityError(
                        f"cannot finalize a {projection.status} projection"
                    )
                try:
                    prepared = await _prepare_projection(db, projection)
                except IncompleteProjectionError:
                    await db.rollback()
                    raise
                except ProjectionIntegrityError as exc:
                    await _mark_failed(db, projection_id, str(exc))
                    raise
                await db.commit()

                embeddings = await embed_texts([chunk.content for chunk in prepared.chunks])
                try:
                    async with db.begin():
                        return await _activate_projection(db, prepared, embeddings)
                except ProjectionIntegrityError as exc:
                    await _mark_failed(db, projection_id, str(exc))
                    raise
        finally:
            await connection.execute(
                text("SELECT pg_advisory_unlock(hashtextextended(:projection_id, 0))"),
                {"projection_id": projection_id},
            )
            await connection.commit()
