import asyncio
from types import SimpleNamespace

import scripts.backfill_document_hashes as backfill
from scripts.backfill_document_hashes import sha256_path


def test_sha256_path_hashes_file_bytes(tmp_path):
    source = tmp_path / "note.md"
    source.write_bytes(b"atomic notes")
    assert sha256_path(source) == "6fac78f37c3d30032a379a77ab50a48e972e1a1d2d32ce630a51f6f08e81e8e1"


class FakeDatabase:
    def __init__(self):
        self.flushes = 0
        self.commits = 0

    async def flush(self):
        self.flushes += 1

    async def commit(self):
        self.commits += 1


def legacy_document(pk, document_id, path, *, kb_pk=1):
    return SimpleNamespace(
        pk=pk,
        id=document_id,
        file_path=str(path),
        file_name=" Notes.MD ",
        knowledge_base_pk=kb_pk,
        content_sha256=None,
        normalized_file_name="",
        duplicate_of_document_id=None,
        version_group_id="",
    )


def test_backfill_preserves_duplicate_rows_and_marks_later_copy(monkeypatch, tmp_path):
    first_path = tmp_path / "first.md"
    second_path = tmp_path / "second.md"
    first_path.write_bytes(b"same")
    second_path.write_bytes(b"same")
    first = legacy_document(1, "doc-1", first_path)
    second = legacy_document(2, "doc-2", second_path)

    async def list_batch(*args, **kwargs):
        return [first, second]

    async def no_existing(*args, **kwargs):
        return None

    monkeypatch.setattr(backfill, "list_unhashed_documents", list_batch)
    monkeypatch.setattr(backfill, "find_canonical_by_hash", no_existing)
    database = FakeDatabase()
    result = asyncio.run(backfill.backfill_batch(database))

    assert result == (2, 2, 0)
    assert first.duplicate_of_document_id is None
    assert second.duplicate_of_document_id == "doc-1"
    assert first.content_sha256 == second.content_sha256
    assert first.normalized_file_name == second.normalized_file_name == "notes.md"
    assert database.commits == 1


def test_missing_raw_file_advances_cursor_and_reports_failure(monkeypatch, tmp_path):
    missing = legacy_document(42, "doc-missing", tmp_path / "absent.md")

    async def list_batch(*args, **kwargs):
        return [missing]

    monkeypatch.setattr(backfill, "list_unhashed_documents", list_batch)
    database = FakeDatabase()
    result = asyncio.run(backfill.backfill_batch(database, after_pk=10))
    assert result == (1, 42, 1)
    assert database.commits == 1


def test_canonical_lookup_resolves_prior_batch_document(monkeypatch, tmp_path):
    path = tmp_path / "later.md"
    path.write_bytes(b"same")
    later = legacy_document(9, "doc-later", path)
    prior = SimpleNamespace(id="doc-prior")

    async def list_batch(*args, **kwargs):
        return [later]

    async def existing(*args, **kwargs):
        return prior

    monkeypatch.setattr(backfill, "list_unhashed_documents", list_batch)
    monkeypatch.setattr(backfill, "find_canonical_by_hash", existing)
    asyncio.run(backfill.backfill_batch(FakeDatabase(), after_pk=8))
    assert later.duplicate_of_document_id == "doc-prior"


def test_backfill_runner_finishes_scan_and_exits_nonzero_after_missing_file(monkeypatch):
    batches = iter([(1, 42, 1), (0, 42, 0)])

    async def batch(*args, **kwargs):
        return next(batches)

    class SessionContext:
        async def __aenter__(self):
            return FakeDatabase()

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(backfill, "backfill_batch", batch)
    monkeypatch.setattr(backfill, "AsyncSessionLocal", lambda: SessionContext())
    assert asyncio.run(backfill.run_backfill()) == 1
