from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from app.mneme.conf.database import AsyncSessionLocal
from app.mneme.conf.logging import app_logger
from app.mneme.crud.document import find_canonical_by_hash, list_unhashed_documents
from app.mneme.domains.documents.upload_service import normalize_file_name


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


async def backfill_batch(db, *, after_pk: int = 0, batch_size: int = 100) -> tuple[int, int, int]:
    documents = await list_unhashed_documents(db, after_pk=after_pk, limit=batch_size)
    canonical_by_hash = {}
    failed = 0
    for document in documents:
        raw_path = Path(document.file_path)
        if not raw_path.is_file():
            app_logger.bind(module="document_hash_backfill").error(
                f"raw file missing document_id={document.id}"
            )
            failed += 1
            continue
        digest = await asyncio.to_thread(sha256_path, raw_path)
        key = (document.knowledge_base_pk, digest)
        canonical = canonical_by_hash.get(key)
        if canonical is None:
            canonical = await find_canonical_by_hash(
                db,
                knowledge_base_pk=document.knowledge_base_pk,
                content_sha256=digest,
            )
        if canonical is None:
            canonical = document
            canonical_by_hash[key] = document
        document.content_sha256 = digest
        document.normalized_file_name = normalize_file_name(document.file_name)
        document.duplicate_of_document_id = None if document.id == canonical.id else canonical.id
        if not document.version_group_id:
            document.version_group_id = document.id
        await db.flush()
    await db.commit()
    return len(documents), (documents[-1].pk if documents else after_pk), failed


async def run_backfill(*, batch_size: int = 100) -> int:
    after_pk = 0
    failed = 0
    async with AsyncSessionLocal() as db:
        while True:
            count, after_pk, batch_failed = await backfill_batch(
                db,
                after_pk=after_pk,
                batch_size=batch_size,
            )
            failed += batch_failed
            if count == 0:
                break
    return 1 if failed else 0


def main() -> int:
    try:
        return asyncio.run(run_backfill())
    except Exception as exc:
        app_logger.bind(module="document_hash_backfill").exception(
            f"document hash backfill failed error={exc}"
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
