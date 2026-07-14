import argparse
import asyncio
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy import select

from app.mneme.conf.database import engine, open_read_session, open_write_session
from app.mneme.domains.documents.agent_projection import build_document_projection_batches
from app.mneme.domains.tasks.outbox import (
    enqueue_document_agent_projection,
    enqueue_user_memory_requested,
)
from app.mneme.models.document import Document
from app.mneme.models.memory_entry import MemoryEntry

DEFAULT_CHECKPOINT = Path(".mneme-agent-backfill-checkpoint.json")


@dataclass(frozen=True)
class Checkpoint:
    kind: str
    source_id: str
    projection_id: str | None
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
    return Checkpoint(**raw)


def _synthetic_id(prefix: str, source_id: str) -> str:
    digest = hashlib.sha256(source_id.encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:48]}"


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
    if kind == "document" and checkpoint.projection_id == projection_id:
        return True
    return source_id > checkpoint.source_id


async def run_backfill(args: argparse.Namespace) -> dict[str, int]:
    checkpoint_path = Path(args.checkpoint)
    checkpoint = None if args.resume_from else _load_checkpoint(checkpoint_path)
    explicit_document_resume_seen = args.resume_from is None or args.resume_kind != "document"

    counts = {
        "document_events": 0,
        "legacy_memory_events": 0,
        "secret_filtered": 0,
        "dry_run_events": 0,
    }
    for document in await _documents(
        owner_id=args.owner_id, knowledge_base_id=args.knowledge_base_id
    ):
        async with open_read_session() as db:
            events = await build_document_projection_batches(
                db, document=document, batch_size=args.batch_size
            )
        projection_id = str(events[0].payload["projection_id"])
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
        for event in events:
            batch_index = int(event.payload["batch_index"])
            if (
                (
                    checkpoint is not None
                    and checkpoint.kind == "document"
                    and checkpoint.projection_id == projection_id
                    and checkpoint.batch_index is not None
                    and batch_index <= checkpoint.batch_index
                )
                or (
                    args.resume_from in {document.id, projection_id}
                    and args.resume_batch_index is not None
                    and batch_index <= args.resume_batch_index
                )
            ):
                continue
            if args.dry_run:
                counts["dry_run_events"] += 1
                continue
            async with open_write_session() as db:
                await enqueue_document_agent_projection(db, event=event)
            _atomic_checkpoint(
                checkpoint_path,
                Checkpoint(
                    kind="document",
                    source_id=document.id,
                    projection_id=projection_id,
                    batch_index=batch_index,
                    event_id=event.event_id,
                    status="accepted",
                ),
            )
            counts["document_events"] += 1

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
        occurred_at = memory.first_seen_at
        async with open_write_session() as db:
            outbox_event = await enqueue_user_memory_requested(
                db,
                owner_id=memory.user_id,
                knowledge_base_id=memory.knowledge_base_id,
                session_id=_synthetic_id("legacy_session", memory.id),
                message_id=_synthetic_id("legacy_message", memory.id),
                excerpt=memory.summary,
                message_created_at=occurred_at,
            )
        status = "accepted" if outbox_event is not None else "secret_filtered"
        _atomic_checkpoint(
            checkpoint_path,
            Checkpoint(
                kind="legacy_memory",
                source_id=memory.id,
                projection_id=None,
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
