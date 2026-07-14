import argparse
import asyncio
import hashlib
import json

from sqlalchemy import select

from services.memory_agent.database import engine, open_read_session
from services.memory_agent.models.document_chunk import DocumentChunk
from services.memory_agent.models.document_projection import DocumentProjection
from services.memory_agent.models.projection_batch import DocumentProjectionBatch


def _content_hashes_match(raw_chunks: list[dict]) -> bool:
    return all(
        isinstance(chunk.get("content"), str)
        and hashlib.sha256(chunk["content"].encode("utf-8")).hexdigest()
        == chunk.get("content_hash")
        for chunk in raw_chunks
    )


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
    counts = {"staged": 0, "active": 0, "failed": 0, "superseded": 0, "hash_mismatch": 0}
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
            raw_chunks = [chunk for batch in batches for chunk in batch.chunks]
            hashes = [str(chunk.get("content_hash", "")) for chunk in raw_chunks]
            aggregate_hash = hashlib.sha256("".join(hashes).encode("ascii")).hexdigest()
            hash_mismatch = (
                not _content_hashes_match(raw_chunks)
                or aggregate_hash != projection.aggregate_hash
            )
            if projection.status == "active":
                active_chunks = list(
                    await db.scalars(
                        select(DocumentChunk).where(
                            DocumentChunk.projection_id == projection.projection_id,
                            DocumentChunk.is_active.is_(True),
                        )
                    )
                )
                hash_mismatch = hash_mismatch or len(active_chunks) != len(raw_chunks) or any(
                    hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
                    != chunk.content_hash
                    for chunk in active_chunks
                )
            status_key = "staged" if projection.status == "staging" else projection.status
            counts[status_key] += 1
            counts["hash_mismatch"] += int(hash_mismatch)
            records.append(
                {
                    "projection_id": projection.projection_id,
                    "document_id": projection.document_id,
                    "status": projection.status,
                    "batch_count": len(batches),
                    "chunk_count": len(raw_chunks),
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
