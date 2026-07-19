import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

import app.mneme.crud.document as document_crud
from app.mneme.conf.database import get_database
from app.mneme.domains.documents.router import router
from app.mneme.utils.auth import get_current_user


class WorkspaceRowsResult:
    def all(self):
        return []


class ScalarResult:
    def __init__(self, documents):
        self.documents = documents

    def scalars(self):
        return self

    def all(self):
        return self.documents


class StatementCaptureDatabase:
    def __init__(self, result=None):
        self.statements = []
        self.result = result or WorkspaceRowsResult()

    async def execute(self, statement):
        self.statements.append(statement)
        return self.result


def test_shared_list_documents_returns_document_scalars_without_folder_join():
    document = SimpleNamespace(id="doc-shared")
    database = StatementCaptureDatabase(ScalarResult([document]))

    result = asyncio.run(document_crud.list_documents(database, user_id=7, knowledge_base_pk=11))

    assert result == [document]
    sql = str(database.statements[0].compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    ))
    assert "JOIN document_folders" not in sql
    assert "documents.user_id = 7" in sql
    assert "documents.knowledge_base_pk = 11" in sql
    assert "ORDER BY documents.created_at DESC" in sql


def test_workspace_list_joins_owned_same_kb_folder_in_one_query():
    database = StatementCaptureDatabase()

    asyncio.run(document_crud.list_document_workspace_rows(database, user_id=7, knowledge_base_pk=11))

    assert len(database.statements) == 1
    sql = str(database.statements[0].compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    ))
    assert "JOIN document_folders" in sql
    assert "documents.folder_pk = document_folders.pk" in sql
    assert "documents.user_id = document_folders.user_id" in sql
    assert "documents.knowledge_base_pk = document_folders.knowledge_base_pk" in sql
    assert "WHERE documents.user_id = 7 AND documents.knowledge_base_pk = 11" in sql
    assert "ORDER BY documents.created_at DESC" in sql


def test_graph_admin_consumer_receives_document_models_from_shared_list(monkeypatch):
    import app.mneme.domains.graph.admin as graph_admin

    document = SimpleNamespace(id="doc-graph")
    database = StatementCaptureDatabase(ScalarResult([document]))
    knowledge_base = SimpleNamespace(id="kb-owned", pk=11, user_id=7)
    projected = []

    async def get_kb(*args, **kwargs):
        return knowledge_base

    async def no_op(*args, **kwargs):
        return None

    async def no_memories(*args, **kwargs):
        return []

    async def project_document(*args, **kwargs):
        projected.append(kwargs["document"])

    monkeypatch.setattr(graph_admin, "is_neo4j_projection_enabled", lambda: True)
    monkeypatch.setattr(graph_admin, "get_knowledge_base_by_id", get_kb)
    monkeypatch.setattr(graph_admin, "list_documents", document_crud.list_documents)
    monkeypatch.setattr(graph_admin, "sync_user_projection", no_op)
    monkeypatch.setattr(graph_admin, "sync_knowledge_base_projection", no_op)
    monkeypatch.setattr(graph_admin, "list_memory_entries_by_document_id", no_memories)
    monkeypatch.setattr(graph_admin, "sync_document_memory_projection", project_document)
    monkeypatch.setattr(graph_admin, "rebuild_user_related_projection", no_op)

    result = asyncio.run(graph_admin.rebuild_graph_projection_for_knowledge_base(
        database,
        current_user=SimpleNamespace(id=7),
        knowledge_base_id="kb-owned",
    ))

    assert projected == [document]
    assert result["document_count"] == 1


def test_document_list_serializes_public_folder_and_version_metadata(monkeypatch):
    import app.mneme.domains.documents.router as documents_router

    created_at = datetime(2026, 7, 12, tzinfo=UTC)
    base = {
        "user_id": 7,
        "knowledge_base_id": "kb-owned",
        "knowledge_base_pk": 11,
        "file_type": "md",
        "status": "indexed",
        "created_at": created_at,
    }
    root_doc = SimpleNamespace(
        **base,
        id="doc-root-v1",
        file_name="notes.md",
        folder_pk=1,
        version_group_id="vg-notes",
        version_number=1,
        duplicate_of_document_id=None,
    )
    version = SimpleNamespace(
        **base,
        id="doc-nested-v2",
        file_name="notes.md",
        folder_pk=2,
        version_group_id="vg-notes",
        version_number=2,
        duplicate_of_document_id=None,
    )
    legacy_duplicate = SimpleNamespace(
        **base,
        id="doc-legacy-copy",
        file_name="copy.md",
        folder_pk=2,
        version_group_id="vg-copy",
        version_number=1,
        duplicate_of_document_id="doc-root-v1",
    )

    async def owned_kb(*args, **kwargs):
        return SimpleNamespace(pk=11, id="kb-owned", user_id=7)

    async def listed(*args, **kwargs):
        return [
            (root_doc, "fld-root-public"),
            (version, "fld-research-public"),
            (legacy_duplicate, "fld-research-public"),
        ]

    monkeypatch.setattr(documents_router, "get_knowledge_base_by_id", owned_kb)
    monkeypatch.setattr(documents_router, "list_document_workspace_rows", listed)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
    app.dependency_overrides[get_database] = lambda: SimpleNamespace()
    with TestClient(app) as client:
        response = client.get("/kb/documents", params={"knowledge_base_id": "kb-owned"})

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert items == [
        {
            "id": "doc-root-v1", "user_id": 7, "knowledge_base_id": "kb-owned",
            "folder_id": "fld-root-public", "file_name": "notes.md", "file_type": "md",
            "status": "indexed", "version_group_id": "vg-notes", "version_number": 1,
            "duplicate_of_document_id": None, "created_at": created_at.isoformat().replace("+00:00", "Z"),
        },
        {
            "id": "doc-nested-v2", "user_id": 7, "knowledge_base_id": "kb-owned",
            "folder_id": "fld-research-public", "file_name": "notes.md", "file_type": "md",
            "status": "indexed", "version_group_id": "vg-notes", "version_number": 2,
            "duplicate_of_document_id": None, "created_at": created_at.isoformat().replace("+00:00", "Z"),
        },
        {
            "id": "doc-legacy-copy", "user_id": 7, "knowledge_base_id": "kb-owned",
            "folder_id": "fld-research-public", "file_name": "copy.md", "file_type": "md",
            "status": "indexed", "version_group_id": "vg-copy", "version_number": 1,
            "duplicate_of_document_id": "doc-root-v1", "created_at": created_at.isoformat().replace("+00:00", "Z"),
        },
    ]
