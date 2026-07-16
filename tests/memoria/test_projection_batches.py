import asyncio
import hashlib
from types import SimpleNamespace

import pytest

from app.mneme.memoria.server.contracts.events import DocumentChunkPayload
from app.mneme.memoria.server.repositories.projections import ProjectionIntegrityError
from app.mneme.memoria.server.services.projections import IncompleteProjectionError, _prepare_projection


def _chunk(chunk_id: str, index: int, content: str) -> DocumentChunkPayload:
    return DocumentChunkPayload(
        chunk_id=chunk_id,
        chunk_index=index,
        content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )


def _projection(*, chunks: list[DocumentChunkPayload], batch_indexes: list[int]):
    hashes = "".join(chunk.content_hash for chunk in sorted(chunks, key=lambda item: item.chunk_index))
    aggregate = hashlib.sha256(hashes.encode("ascii")).hexdigest()
    return SimpleNamespace(
        projection_id="projection-1",
        owner_id=7,
        knowledge_base_id="kb-1",
        document_id="doc-1",
        document_version="v1",
        batch_count=len(batch_indexes),
        aggregate_hash=aggregate,
    )


class _ScalarRows:
    def __init__(self, rows):
        self.rows = rows

    async def scalars(self, statement):
        return self.rows


def test_prepare_projection_rejects_missing_or_out_of_order_batches():
    chunks = [_chunk("c0", 0, "first"), _chunk("c1", 1, "second")]
    projection = _projection(chunks=chunks, batch_indexes=[0, 1])
    db = _ScalarRows(
        [SimpleNamespace(batch_index=1, chunks=[chunks[1].model_dump(mode="json")])]
    )

    with pytest.raises(IncompleteProjectionError, match="requires batch indexes"):
        asyncio.run(_prepare_projection(db, projection))


def test_prepare_projection_accepts_batches_arriving_in_any_storage_order():
    chunks = [_chunk("c0", 0, "first"), _chunk("c1", 1, "second")]
    projection = _projection(chunks=chunks, batch_indexes=[0, 1])
    db = _ScalarRows(
        [
            SimpleNamespace(batch_index=0, chunks=[chunks[0].model_dump(mode="json")]),
            SimpleNamespace(batch_index=1, chunks=[chunks[1].model_dump(mode="json")]),
        ]
    )

    prepared = asyncio.run(_prepare_projection(db, projection))

    assert [chunk.chunk_id for chunk in prepared.chunks] == ["c0", "c1"]
    assert len(prepared.snapshot_hash) == 64


def test_prepare_projection_rejects_duplicate_chunk_and_aggregate_hash():
    chunks = [_chunk("c0", 0, "first"), _chunk("c0", 1, "second")]
    projection = _projection(chunks=chunks, batch_indexes=[0])
    db = _ScalarRows(
        [SimpleNamespace(batch_index=0, chunks=[chunk.model_dump(mode="json") for chunk in chunks])]
    )

    with pytest.raises(ProjectionIntegrityError, match="chunk IDs must be unique"):
        asyncio.run(_prepare_projection(db, projection))

    projection.aggregate_hash = "0" * 64
    chunks = [_chunk("c0", 0, "first")]
    projection = _projection(chunks=chunks, batch_indexes=[0])
    projection.aggregate_hash = "0" * 64
    db = _ScalarRows([SimpleNamespace(batch_index=0, chunks=[chunks[0].model_dump(mode="json")])])
    with pytest.raises(ProjectionIntegrityError, match="aggregate hash mismatch"):
        asyncio.run(_prepare_projection(db, projection))
