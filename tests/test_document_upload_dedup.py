import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError
import pytest

import app.mneme.domains.documents.upload_service as service
from app.mneme.domains.documents.upload_service import normalize_file_name, next_version
from app.mneme.schemas.document import DocumentUploadData


class AsyncBytesFile:
    def __init__(self, name: str, chunks: list[bytes]):
        self.filename = name
        self._chunks = iter(chunks)

    async def read(self, _size: int):
        return next(self._chunks, b"")


class FakeDatabase:
    @asynccontextmanager
    async def begin_nested(self):
        yield


def document(**overrides):
    values = {
        "pk": 8,
        "id": "doc-existing",
        "user_id": 7,
        "knowledge_base_id": "kb-1",
        "knowledge_base_pk": 11,
        "folder_pk": 2,
        "file_name": "existing.md",
        "file_type": "md",
        "file_size": 4,
        "status": "uploaded",
        "version_group_id": "doc-existing",
        "version_number": 1,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def destination():
    return (
        SimpleNamespace(id=7),
        SimpleNamespace(pk=11, id="kb-1", user_id=7),
        SimpleNamespace(
            pk=2,
            id="fld-notes",
            user_id=7,
            knowledge_base_pk=11,
            parent_pk=1,
            name="Notes",
            is_root=False,
        ),
    )


def install_folder_lookup(monkeypatch):
    folders = {
        2: SimpleNamespace(pk=2, id="fld-notes", parent_pk=1, name="Notes", is_root=False),
        1: SimpleNamespace(pk=1, id="fld-root", parent_pk=1, name="/", is_root=True),
    }

    async def get_folder(*args, folder_pk, **kwargs):
        return folders[folder_pk]

    monkeypatch.setattr(service, "get_folder_by_pk", get_folder)


def test_file_name_normalization_is_case_insensitive():
    assert normalize_file_name("  Notes.MD ") == "notes.md"


def test_next_version_links_latest_document():
    version = next_version(latest_id="doc-v2", latest_version=2, group_id="doc-v1")
    assert version == {
        "version_group_id": "doc-v1",
        "version_number": 3,
        "previous_document_id": "doc-v2",
    }


def test_exact_bytes_anywhere_in_kb_return_duplicate_without_creating(monkeypatch, tmp_path):
    install_folder_lookup(monkeypatch)
    monkeypatch.setattr(service.settings, "RAW_FILE_DIR", tmp_path)
    canonical = document(folder_pk=2, file_name="canonical.md")
    creates = []

    async def find_canonical(*args, **kwargs):
        return canonical

    async def never_create(*args, **kwargs):
        creates.append(kwargs)

    monkeypatch.setattr(service, "find_canonical_by_hash", find_canonical)
    monkeypatch.setattr(service, "create_document", never_create)
    user, kb, folder = destination()
    result = asyncio.run(service.store_uploaded_document(
        FakeDatabase(), file=AsyncBytesFile("renamed.md", [b"same", b""]),
        current_user=user, knowledge_base=kb, folder=folder,
    ))

    assert result.disposition == "duplicate"
    assert result.document_id == canonical.id
    assert creates == []
    assert list(tmp_path.iterdir()) == []


def test_same_name_different_bytes_in_same_folder_creates_next_version(monkeypatch, tmp_path):
    install_folder_lookup(monkeypatch)
    monkeypatch.setattr(service.settings, "RAW_FILE_DIR", tmp_path)
    latest = document(id="doc-v2", version_group_id="doc-v1", version_number=2)
    captured = {}

    async def no_canonical(*args, **kwargs):
        return None

    async def latest_version(*args, **kwargs):
        assert kwargs["folder_pk"] == 2
        assert kwargs["normalized_file_name"] == "notes.md"
        return latest

    async def create(*args, **kwargs):
        captured.update(kwargs)
        return document(
            id=kwargs["document_id"], file_name=kwargs["file_name"],
            file_size=kwargs["file_size"], version_group_id=kwargs["version_group_id"],
            version_number=kwargs["version_number"], folder_pk=kwargs["folder_pk"],
        )

    monkeypatch.setattr(service, "find_canonical_by_hash", no_canonical)
    monkeypatch.setattr(service, "find_latest_version", latest_version)
    monkeypatch.setattr(service, "create_document", create)
    user, kb, folder = destination()
    result = asyncio.run(service.store_uploaded_document(
        FakeDatabase(), file=AsyncBytesFile(" Notes.MD ", [b"changed"]),
        current_user=user, knowledge_base=kb, folder=folder,
    ))

    assert result.disposition == "created"
    assert captured["version_group_id"] == "doc-v1"
    assert captured["version_number"] == 3
    assert captured["previous_document_id"] == "doc-v2"
    assert Path(captured["file_path"]).is_file()


def test_same_name_in_different_folder_starts_independent_v1(monkeypatch, tmp_path):
    install_folder_lookup(monkeypatch)
    monkeypatch.setattr(service.settings, "RAW_FILE_DIR", tmp_path)
    captured = {}

    async def no_match(*args, **kwargs):
        return None

    async def create(*args, **kwargs):
        captured.update(kwargs)
        return document(
            id=kwargs["document_id"], file_name=kwargs["file_name"],
            file_size=kwargs["file_size"], version_group_id=kwargs["version_group_id"],
            version_number=kwargs["version_number"], folder_pk=kwargs["folder_pk"],
        )

    monkeypatch.setattr(service, "find_canonical_by_hash", no_match)
    monkeypatch.setattr(service, "find_latest_version", no_match)
    monkeypatch.setattr(service, "create_document", create)
    user, kb, folder = destination()
    result = asyncio.run(service.store_uploaded_document(
        FakeDatabase(), file=AsyncBytesFile("notes.md", [b"new folder bytes"]),
        current_user=user, knowledge_base=kb, folder=folder,
    ))
    assert captured["version_number"] == 1
    assert captured["version_group_id"] == result.document_id
    assert captured["previous_document_id"] is None


def test_unique_index_race_removes_loser_file_and_resolves_winner(monkeypatch, tmp_path):
    install_folder_lookup(monkeypatch)
    monkeypatch.setattr(service.settings, "RAW_FILE_DIR", tmp_path)
    canonical_path = tmp_path / "doc-winner__race.md"
    canonical_path.write_bytes(b"racing bytes")
    winner = document(id="doc-winner", file_path=str(canonical_path))
    canonical_results = iter([None, winner])

    async def find_canonical(*args, **kwargs):
        return next(canonical_results)

    async def no_latest(*args, **kwargs):
        return None

    async def racing_create(*args, **kwargs):
        raise IntegrityError("insert", {}, Exception("canonical race"))

    monkeypatch.setattr(service, "find_canonical_by_hash", find_canonical)
    monkeypatch.setattr(service, "find_latest_version", no_latest)
    monkeypatch.setattr(service, "create_document", racing_create)
    user, kb, folder = destination()
    result = asyncio.run(service.store_uploaded_document(
        FakeDatabase(), file=AsyncBytesFile("race.md", [b"racing bytes"]),
        current_user=user, knowledge_base=kb, folder=folder,
    ))
    assert result.disposition == "duplicate"
    assert result.document_id == "doc-winner"
    assert list(tmp_path.iterdir()) == [canonical_path]
    assert canonical_path.read_bytes() == b"racing bytes"


def test_oversize_stream_cleans_request_temp_file(monkeypatch, tmp_path):
    monkeypatch.setattr(service.settings, "RAW_FILE_DIR", tmp_path)
    monkeypatch.setattr(service.settings, "MAX_FILE_SIZE", 3)
    user, kb, folder = destination()
    with pytest.raises(Exception, match="less than 3"):
        asyncio.run(service.store_uploaded_document(
            FakeDatabase(), file=AsyncBytesFile("large.md", [b"1234"]),
            current_user=user, knowledge_base=kb, folder=folder,
        ))
    assert list(tmp_path.iterdir()) == []


def test_unexpected_insert_failure_cleans_moved_final_file(monkeypatch, tmp_path):
    monkeypatch.setattr(service.settings, "RAW_FILE_DIR", tmp_path)

    async def no_match(*args, **kwargs):
        return None

    async def fail_create(*args, **kwargs):
        raise RuntimeError("insert failed")

    monkeypatch.setattr(service, "find_canonical_by_hash", no_match)
    monkeypatch.setattr(service, "find_latest_version", no_match)
    monkeypatch.setattr(service, "create_document", fail_create)
    user, kb, folder = destination()
    with pytest.raises(RuntimeError, match="insert failed"):
        asyncio.run(service.store_uploaded_document(
            FakeDatabase(), file=AsyncBytesFile("broken.md", [b"bytes"]),
            current_user=user, knowledge_base=kb, folder=folder,
        ))
    assert list(tmp_path.iterdir()) == []


def upload_data(disposition):
    return DocumentUploadData(
        disposition=disposition,
        document_id="doc-created" if disposition == "created" else "doc-existing",
        canonical_document_id="doc-created" if disposition == "created" else "doc-existing",
        user_id=7,
        knowledge_base_id="kb-1",
        folder_id="fld-root",
        folder_path=[],
        file_name="notes.md",
        file_type="md",
        file_size=5,
        status="uploaded",
        version_group_id="doc-created",
        version_number=1,
    )


def test_route_projects_only_created_uploads(monkeypatch):
    import app.mneme.domains.documents.router as router

    user, kb, folder = destination()
    projected = []

    async def get_kb(*args, **kwargs):
        return kb

    async def root(*args, **kwargs):
        return folder

    async def store(*args, **kwargs):
        return upload_data("created")

    created = document(id="doc-created")

    async def get_document(*args, **kwargs):
        return created

    async def project(**kwargs):
        projected.append(kwargs["document"].id)

    monkeypatch.setattr(router, "enforce_fixed_window_rate_limit", lambda **kwargs: None)
    monkeypatch.setattr(router, "get_knowledge_base_by_id", get_kb)
    monkeypatch.setattr(router, "ensure_root_folder", root)
    monkeypatch.setattr(router, "store_uploaded_document", store)
    monkeypatch.setattr(router, "get_document_by_id", get_document)
    monkeypatch.setattr(router, "sync_document_projection", project)
    response = asyncio.run(router.upload_document(
        user_id=None,
        knowledge_base_id="kb-1",
        folder_id=None,
        file=AsyncBytesFile("notes.md", [b"notes"]),
        current_user=user,
        db=FakeDatabase(),
    ))
    assert response.data.disposition == "created"
    assert projected == ["doc-created"]


def test_route_duplicate_never_projects_or_resolves_new_document(monkeypatch):
    import app.mneme.domains.documents.router as router

    user, kb, folder = destination()
    forbidden = []

    async def get_kb(*args, **kwargs):
        return kb

    async def root(*args, **kwargs):
        return folder

    async def store(*args, **kwargs):
        return upload_data("duplicate")

    async def forbidden_call(*args, **kwargs):
        forbidden.append(True)
        raise AssertionError("duplicate upload must not project")

    monkeypatch.setattr(router, "enforce_fixed_window_rate_limit", lambda **kwargs: None)
    monkeypatch.setattr(router, "get_knowledge_base_by_id", get_kb)
    monkeypatch.setattr(router, "ensure_root_folder", root)
    monkeypatch.setattr(router, "store_uploaded_document", store)
    monkeypatch.setattr(router, "get_document_by_id", forbidden_call)
    monkeypatch.setattr(router, "sync_document_projection", forbidden_call)
    response = asyncio.run(router.upload_document(
        user_id=None,
        knowledge_base_id="kb-1",
        folder_id=None,
        file=AsyncBytesFile("notes.md", [b"notes"]),
        current_user=user,
        db=FakeDatabase(),
    ))
    assert response.data.disposition == "duplicate"
    assert forbidden == []
