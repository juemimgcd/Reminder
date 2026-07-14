import argparse
import asyncio
import hashlib
import json

from sqlalchemy import select

from services.memory_agent.database import engine, open_read_session
from services.memory_agent.models.document_chunk import DocumentChunk
from services.memory_agent.models.document_projection import DocumentProjection
from services.memory_agent.models.projection_batch import DocumentProjectionBatch


def _raw_chunk_map(raw_chunks: list[dict]) -> tuple[dict[tuple[int, str], dict], bool]:
    mapped: dict[tuple[int, str], dict] = {}
    valid = True
    for chunk in raw_chunks:
        chunk_index = chunk.get("chunk_index")
        chunk_id = chunk.get("chunk_id")
        content = chunk.get("content")
        content_hash = chunk.get("content_hash")
        if (
            not isinstance(chunk_index, int)
            or not isinstance(chunk_id, str)
            or not isinstance(content, str)
            or not isinstance(content_hash, str)
        ):
            valid = False
            continue
        key = (chunk_index, chunk_id)
        if key in mapped:
            valid = False
        mapped[key] = chunk
        valid = valid and hashlib.sha256(content.encode("utf-8")).hexdigest() == content_hash
    return mapped, valid


def _aggregate_hash(raw_map: dict[tuple[int, str], dict]) -> str:
    hashes = [str(raw_map[key]["content_hash"]) for key in sorted(raw_map)]
    return hashlib.sha256("".join(hashes).encode("ascii")).hexdigest()


async def projection_report(args: argparse.Namespace) -> dict:
    statement = select(DocumentProjection)
    if args.owner_id is not None:
        statement = statement.where(DocumentProjection.owner_id == args.owner_id)
    if args.knowledge_base_id is not None:
        statement = statement.where(
            DocumentProjection.knowledge_base_id == args.knowledge_base_id
        )
    if args.resume_from:
        statement = statement.where(DocumentProjection.projection_id > args.resume_from)
    statement = statement.order_by(DocumentProjection.projection_id).limit(args.batch_size)

    records = []
    counts = {
        "staged": 0,
        "active": 0,
        "failed": 0,
        "superseded": 0,
        "hash_mismatch": 0,
        "batch_mismatch": 0,
        "chunk_key_mismatch": 0,
        "scope_mismatch": 0,
    }
    async with open_read_session() as db:
        projections = list(await db.scalars(statement))
        for projection in projections:
            batches = list(
                await db.scalars(
                    select(DocumentProjectionBatch)
                    .where(DocumentProjectionBatch.projection_id == projection.projection_id)
                    .order_by(DocumentProjectionBatch.batch_index)
                )
            )
            batch_indexes = [batch.batch_index for batch in batches]
            batch_mismatch = batch_indexes != list(range(projection.batch_count))
            raw_chunks = [chunk for batch in batches for chunk in batch.chunks]
            raw_map, raw_hashes_match = _raw_chunk_map(raw_chunks)
            raw_keys = sorted(raw_map)
            try:
                aggregate_hash = _aggregate_hash(raw_map)
            except UnicodeEncodeError:
                aggregate_hash = ""
            hash_mismatch = (
                not raw_hashes_match
                or aggregate_hash != projection.aggregate_hash
            )
            chunk_key_mismatch = (
                [key[0] for key in raw_keys] != list(range(len(raw_keys)))
                or len({key[1] for key in raw_keys}) != len(raw_keys)
                or len(raw_map) != len(raw_chunks)
            )
            scope_mismatch = (
                projection.owner_id <= 0
                or not projection.knowledge_base_id
                or not projection.document_id
                or not projection.document_version
            )
            if projection.status == "active":
                active_chunks = list(
                    await db.scalars(
                        select(DocumentChunk).where(
                            DocumentChunk.projection_id == projection.projection_id,
                            DocumentChunk.is_active.is_(True),
                        ).order_by(DocumentChunk.chunk_index, DocumentChunk.chunk_id)
                    )
                )
                active_map = {
                    (chunk.chunk_index, chunk.chunk_id): chunk for chunk in active_chunks
                }
                chunk_key_mismatch = chunk_key_mismatch or set(active_map) != set(raw_map)
                scope_mismatch = scope_mismatch or any(
                    chunk.projection_id != projection.projection_id
                    or chunk.owner_id != projection.owner_id
                    or chunk.knowledge_base_id != projection.knowledge_base_id
                    or chunk.document_id != projection.document_id
                    or chunk.document_version != projection.document_version
                    for chunk in active_chunks
                )
                hash_mismatch = hash_mismatch or any(
                    key not in raw_map
                    or chunk.content_hash != raw_map[key]["content_hash"]
                    or hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
                    != chunk.content_hash
                    for key, chunk in active_map.items()
                )
            status_key = "staged" if projection.status == "staging" else projection.status
            counts[status_key] += 1
            counts["hash_mismatch"] += int(hash_mismatch)
            counts["batch_mismatch"] += int(batch_mismatch)
            counts["chunk_key_mismatch"] += int(chunk_key_mismatch)
            counts["scope_mismatch"] += int(scope_mismatch)
            records.append(
                {
                    "projection_id": projection.projection_id,
                    "document_id": projection.document_id,
                    "status": projection.status,
                    "batch_count": len(batches),
                    "chunk_count": len(raw_chunks),
                    "batch_mismatch": batch_mismatch,
                    "chunk_key_mismatch": chunk_key_mismatch,
                    "scope_mismatch": scope_mismatch,
                    "hash_mismatch": hash_mismatch,
                }
            )
    return {"counts": counts, "projections": records, "dry_run": args.dry_run}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report rebuildable Memory Agent projection state without mutating it."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--owner-id", type=int)
    parser.add_argument("--knowledge-base-id")
    parser.add_argument("--resume-from", help="Return projection IDs lexically after this ID.")
    parser.add_argument("--batch-size", type=int, default=100)
    return parser


async def _main() -> None:
    args = _parser().parse_args()
    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be positive")
    if args.owner_id is not None and args.owner_id <= 0:
        raise SystemExit("--owner-id must be positive")
    try:
        print(json.dumps(await projection_report(args), sort_keys=True))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
