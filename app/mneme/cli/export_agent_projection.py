import argparse
import asyncio
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy import select

from app.mneme.conf.database import engine, open_read_session, open_write_session
from app.mneme.domains.documents.agent_projection import (
    build_document_memory_observation_events,
    build_document_projection_batches,
    build_legacy_document_memory_observed_event,
)
from app.mneme.domains.tasks.outbox import (
    enqueue_document_agent_projection,
    enqueue_document_memory_observed,
)
from app.mneme.models.document import Document
from app.mneme.models.memory_entry import MemoryEntry

DEFAULT_CHECKPOINT = Path(".mneme-agent-backfill-checkpoint.json")


@dataclass(frozen=True)
class Checkpoint:
    kind: str
    source_id: str
    projection_id: str | None
    document_version: str | None
    snapshot_identity: str | None
    projection_batch_count: int | None
    event_index: int | None
    batch_index: int | None
    event_id: str | None
    status: str


def _atomic_checkpoint(path: Path, checkpoint: Checkpoint) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(asdict(checkpoint), ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _load_checkpoint(path: Path) -> Checkpoint | None:
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw.setdefault("document_version", None)
    raw.setdefault("snapshot_identity", None)
    raw.setdefault("projection_batch_count", None)
    raw.setdefault("event_index", raw.get("batch_index"))
    return Checkpoint(**raw)


async def _documents(
    *, owner_id: int | None, knowledge_base_id: str | None
) -> list[Document]:
    statement = select(Document).where(Document.status == "indexed")
    if owner_id is not None:
        statement = statement.where(Document.user_id == owner_id)
    if knowledge_base_id is not None:
        statement = statement.where(Document.knowledge_base_id == knowledge_base_id)
    async with open_read_session() as db:
        return list(await db.scalars(statement.order_by(Document.id)))


async def _legacy_memories(
    *, owner_id: int | None, knowledge_base_id: str | None
) -> list[MemoryEntry]:
    statement = select(MemoryEntry).where(MemoryEntry.status == "active")
    if owner_id is not None:
        statement = statement.where(MemoryEntry.user_id == owner_id)
    if knowledge_base_id is not None:
        statement = statement.where(MemoryEntry.knowledge_base_id == knowledge_base_id)
    async with open_read_session() as db:
        return list(await db.scalars(statement.order_by(MemoryEntry.id)))


def _past_checkpoint(
    *, kind: str, source_id: str, projection_id: str | None, checkpoint: Checkpoint | None
) -> bool:
    if checkpoint is None:
        return True
    kind_order = {"document": 0, "legacy_memory": 1}
    current_order = kind_order[kind]
    checkpoint_order = kind_order.get(checkpoint.kind, -1)
    if current_order != checkpoint_order:
        return current_order > checkpoint_order
    if kind == "document" and checkpoint.source_id == source_id:
        return True
    return source_id > checkpoint.source_id


async def run_backfill(args: argparse.Namespace) -> dict[str, int]:
    checkpoint_path = Path(args.checkpoint)
    checkpoint = None if args.resume_from else _load_checkpoint(checkpoint_path)
    explicit_document_resume_seen = args.resume_from is None or args.resume_kind != "document"

    counts = {
        "document_events": 0,
        "document_memory_events": 0,
        "legacy_memory_events": 0,
        "secret_filtered": 0,
        "dry_run_events": 0,
    }
    documents = await _documents(
        owner_id=args.owner_id, knowledge_base_id=args.knowledge_base_id
    )
    documents_by_id = {document.id: document for document in documents}
    for document in documents:
        async with open_read_session() as db:
            projection_events = await build_document_projection_batches(
                db, document=document, batch_size=args.batch_size
            )
            observation_events = await build_document_memory_observation_events(
                db, document=document
            )
        projection_id = str(projection_events[0].payload["projection_id"])
        document_version = str(projection_events[0].payload["document_version"])
        snapshot_identity = str(projection_events[0].payload["aggregate_hash"])
        events = [*projection_events, *observation_events]
        if (
            checkpoint is not None
            and checkpoint.kind == "document"
            and checkpoint.source_id == document.id
            and checkpoint.projection_id == projection_id
        ):
            if checkpoint.document_version not in {None, document_version}:
                raise ValueError("checkpoint document version conflicts with projection ID")
            if checkpoint.snapshot_identity not in {None, snapshot_identity}:
                raise ValueError("checkpoint snapshot conflicts with projection ID")
            if checkpoint.projection_batch_count not in {None, len(projection_events)}:
                raise ValueError("checkpoint batch count differs; resume with the original batch size")
        if not explicit_document_resume_seen:
            if args.resume_from not in {document.id, projection_id}:
                continue
            explicit_document_resume_seen = True
        if not _past_checkpoint(
            kind="document",
            source_id=document.id,
            projection_id=projection_id,
            checkpoint=checkpoint,
        ):
            continue
        for event_index, event in enumerate(events):
            batch_index = (
                int(event.payload["batch_index"])
                if event.event_type == "document.projection.upserted"
                else None
            )
            if (
                (
                    checkpoint is not None
                    and checkpoint.kind == "document"
                    and checkpoint.projection_id == projection_id
                    and checkpoint.document_version in {None, document_version}
                    and checkpoint.snapshot_identity in {None, snapshot_identity}
                    and checkpoint.event_index is not None
                    and event_index <= checkpoint.event_index
                )
                or (
                    args.resume_from in {document.id, projection_id}
                    and args.resume_batch_index is not None
                    and batch_index is not None
                    and batch_index <= args.resume_batch_index
                )
            ):
                continue
            if args.dry_run:
                counts["dry_run_events"] += 1
                continue
            async with open_write_session() as db:
                if event.event_type == "document.projection.upserted":
                    await enqueue_document_agent_projection(db, event=event)
                    status = "accepted"
                else:
                    outbox_event = await enqueue_document_memory_observed(db, event=event)
                    status = "accepted" if outbox_event is not None else "secret_filtered"
            _atomic_checkpoint(
                checkpoint_path,
                Checkpoint(
                    kind="document",
                    source_id=document.id,
                    projection_id=projection_id,
                    document_version=document_version,
                    snapshot_identity=snapshot_identity,
                    projection_batch_count=len(projection_events),
                    event_index=event_index,
                    batch_index=batch_index,
                    event_id=event.event_id,
                    status=status,
                ),
            )
            if event.event_type == "document.projection.upserted":
                counts["document_events"] += 1
            else:
                if status == "secret_filtered":
                    counts["secret_filtered"] += 1
                else:
                    counts["document_memory_events"] += 1

    for memory in await _legacy_memories(
        owner_id=args.owner_id, knowledge_base_id=args.knowledge_base_id
    ):
        if (
            args.resume_from
            and args.resume_kind == "legacy_memory"
            and memory.id <= args.resume_from
        ):
            continue
        if not _past_checkpoint(
            kind="legacy_memory",
            source_id=memory.id,
            projection_id=None,
            checkpoint=checkpoint,
        ):
            continue
        if args.dry_run:
            counts["dry_run_events"] += 1
            continue
        document = documents_by_id.get(memory.document_id)
        if document is None:
            raise ValueError(f"legacy memory {memory.id} has no scoped indexed document")
        event = build_legacy_document_memory_observed_event(
            document=document,
            memory=memory,
        )
        async with open_write_session() as db:
            outbox_event = await enqueue_document_memory_observed(db, event=event)
        status = "accepted" if outbox_event is not None else "secret_filtered"
        _atomic_checkpoint(
            checkpoint_path,
            Checkpoint(
                kind="legacy_memory",
                source_id=memory.id,
                projection_id=None,
                document_version=document.updated_at.isoformat(),
                snapshot_identity=hashlib.sha256(
                    event.payload["excerpt"].encode("utf-8")
                ).hexdigest(),
                projection_batch_count=None,
                event_index=0,
                batch_index=None,
                event_id=outbox_event.payload["event_id"] if outbox_event is not None else None,
                status=status,
            ),
        )
        if outbox_event is None:
            counts["secret_filtered"] += 1
        else:
            counts["legacy_memory_events"] += 1
    if args.resume_from and args.resume_kind == "document" and not explicit_document_resume_seen:
        raise ValueError("--resume-from did not match a document or projection ID")
    return counts


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill Mneme documents and legacy memory through Memory Agent v1 events."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--owner-id", type=int)
    parser.add_argument("--knowledge-base-id")
    parser.add_argument("--resume-from")
    parser.add_argument(
        "--resume-kind", choices=("document", "legacy_memory"), default="document"
    )
    parser.add_argument("--resume-batch-index", type=int)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--checkpoint", default=str(DEFAULT_CHECKPOINT))
    return parser


async def _main() -> None:
    args = _parser().parse_args()
    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be positive")
    if args.owner_id is not None and args.owner_id <= 0:
        raise SystemExit("--owner-id must be positive")
    if args.resume_batch_index is not None and args.resume_batch_index < 0:
        raise SystemExit("--resume-batch-index must be non-negative")
    try:
        result = await run_backfill(args)
        print(json.dumps(result, sort_keys=True))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
