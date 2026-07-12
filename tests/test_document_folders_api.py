from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.mneme.conf.database import get_database, get_write_database
from app.mneme.domains.documents.folders import normalize_folder_name, router, validate_folder_move
from app.mneme.utils.auth import get_current_user
from app.mneme.utils.exceptions import BusinessException, business_exception_handler


class FakeWriteDatabase:
    def __init__(self, *, flush_error: Exception | None = None):
        self.added = []
        self.deleted = []
        self.flush_error = flush_error
        self.commits = 0
        self.rollbacks = 0

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        if self.flush_error is not None:
            error, self.flush_error = self.flush_error, None
            raise error
        for index, value in enumerate(self.added, start=1):
            if getattr(value, "pk", None) is None:
                value.pk = 100 + index

    async def delete(self, value):
        self.deleted.append(value)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


def folder(
    *,
    pk: int,
    folder_id: str,
    kb_pk: int = 10,
    parent_pk: int = 1,
    name: str = "Folder",
    is_root: bool = False,
):
    return SimpleNamespace(
        pk=pk,
        id=folder_id,
        user_id=7,
        knowledge_base_id=f"kb_{kb_pk}",
        knowledge_base_pk=kb_pk,
        parent_pk=parent_pk,
        name=name,
        normalized_name=normalize_folder_name(name),
        is_root=is_root,
    )


@pytest.fixture
def api(monkeypatch):
    import app.mneme.domains.documents.folders as folders

    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(BusinessException, business_exception_handler)
    user = SimpleNamespace(id=7)
    database = FakeWriteDatabase()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_database] = lambda: database
    app.dependency_overrides[get_write_database] = lambda: database
    monkeypatch.setattr(
        folders,
        "get_knowledge_base_by_id",
        lambda *args, **kwargs: None,
    )
    with TestClient(app) as client:
        yield client, database, folders


def test_folder_names_are_casefolded_and_trimmed():
    assert normalize_folder_name("  Research  ") == "research"
    assert normalize_folder_name("  Research   Notes  ") == "research notes"


def test_folder_cannot_move_beneath_descendant():
    with pytest.raises(BusinessException, match="descendant"):
        validate_folder_move(folder_pk=4, new_parent_pk=9, descendant_pks={9, 10})


def test_create_folder_requires_owned_knowledge_base(api, monkeypatch):
    client, _, folders = api

    async def other_users_kb(*args, **kwargs):
        return SimpleNamespace(pk=10, id="kb_10", user_id=99)

    monkeypatch.setattr(folders, "get_knowledge_base_by_id", other_users_kb)
    response = client.post(
        "/kb/document-folders",
        json={"knowledge_base_id": "kb_10", "parent_id": "root", "name": "Notes"},
    )
    assert response.status_code == 403
    assert response.json()["message"] == "knowledge base does not belong to current user"


def test_duplicate_sibling_name_is_deterministic(api, monkeypatch):
    client, database, folders = api
    database.flush_error = IntegrityError("insert", {}, Exception("duplicate"))

    async def owned_kb(*args, **kwargs):
        return SimpleNamespace(pk=10, id="kb_10", user_id=7)

    async def owned_parent(*args, **kwargs):
        return folder(pk=1, folder_id="root", is_root=True)

    monkeypatch.setattr(folders, "get_knowledge_base_by_id", owned_kb)
    monkeypatch.setattr(folders, "get_folder_by_id", owned_parent)
    response = client.post(
        "/kb/document-folders",
        json={"knowledge_base_id": "kb_10", "parent_id": "root", "name": " Notes "},
    )
    assert response.status_code == 409
    assert response.json()["message"] == "folder name already exists"


def test_delete_empty_folder_succeeds(api, monkeypatch):
    client, database, folders = api
    target = folder(pk=4, folder_id="fld_empty")

    async def get_target(*args, **kwargs):
        return target

    async def has_no_contents(*args, **kwargs):
        return False

    monkeypatch.setattr(folders, "get_folder_by_id", get_target)
    monkeypatch.setattr(folders, "folder_has_contents", has_no_contents)
    response = client.delete("/kb/document-folders/fld_empty")
    assert response.status_code == 200
    assert response.json()["data"] == {"id": "fld_empty"}
    assert database.deleted == [target]


def test_delete_non_empty_folder_is_rejected(api, monkeypatch):
    client, database, folders = api
    target = folder(pk=4, folder_id="fld_full")

    async def get_target(*args, **kwargs):
        return target

    async def has_contents(*args, **kwargs):
        return True

    monkeypatch.setattr(folders, "get_folder_by_id", get_target)
    monkeypatch.setattr(folders, "folder_has_contents", has_contents)
    response = client.delete("/kb/document-folders/fld_full")
    assert response.status_code == 400
    assert "not empty" in response.json()["message"]
    assert database.deleted == []


def test_folder_move_rejects_cross_knowledge_base_parent(api, monkeypatch):
    client, _, folders = api
    target = folder(pk=4, folder_id="fld_source", kb_pk=10)
    destination = folder(pk=8, folder_id="fld_other", kb_pk=11)

    async def get_by_id(db, *, folder_id, user_id):
        return {target.id: target, destination.id: destination}.get(folder_id)

    monkeypatch.setattr(folders, "get_folder_by_id", get_by_id)
    response = client.patch(
        "/kb/document-folders/fld_source",
        json={"parent_id": "fld_other"},
    )
    assert response.status_code == 400
    assert "knowledge base" in response.json()["message"]
    assert target.parent_pk == 1


def test_rename_preserves_parent_id(api, monkeypatch):
    client, _, folders = api
    target = folder(pk=4, folder_id="fld_source", parent_pk=2)
    parent = folder(pk=2, folder_id="fld_parent", parent_pk=1)

    async def get_by_id(db, *, folder_id, user_id):
        return target if folder_id == target.id else None

    async def get_by_pk(db, *, folder_pk, user_id):
        return parent if folder_pk == parent.pk else None

    monkeypatch.setattr(folders, "get_folder_by_id", get_by_id)
    monkeypatch.setattr(folders, "get_folder_by_pk", get_by_pk)
    response = client.patch(
        "/kb/document-folders/fld_source",
        json={"name": "  New   Name  "},
    )
    assert response.status_code == 200
    assert response.json()["data"]["parent_id"] == "fld_parent"
    assert response.json()["data"]["name"] == "New Name"


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_root_folder_cannot_be_modified(api, monkeypatch, method):
    client, _, folders = api
    root = folder(pk=1, folder_id="root", name="/", is_root=True)

    async def get_root(*args, **kwargs):
        return root

    monkeypatch.setattr(folders, "get_folder_by_id", get_root)
    if method == "patch":
        response = client.patch("/kb/document-folders/root", json={"name": "Renamed"})
    else:
        response = client.delete("/kb/document-folders/root")
    assert response.status_code == 400
    assert "root folder" in response.json()["message"]


def test_document_move_succeeds_without_rewriting_version_group(api, monkeypatch):
    client, _, folders = api
    document = SimpleNamespace(
        id="doc_1",
        user_id=7,
        knowledge_base_pk=10,
        folder_pk=1,
        version_group_id="vg_keep_me",
    )
    destination = folder(pk=8, folder_id="fld_dest", kb_pk=10)

    async def get_document(*args, **kwargs):
        return document

    async def get_destination(*args, **kwargs):
        return destination

    monkeypatch.setattr(folders, "get_document_by_id", get_document)
    monkeypatch.setattr(folders, "get_folder_by_id", get_destination)
    response = client.post(
        "/kb/document-folders/documents/doc_1/move",
        json={"folder_id": "fld_dest"},
    )
    assert response.status_code == 200
    assert response.json()["data"] == {"document_id": "doc_1", "folder_id": "fld_dest"}
    assert document.folder_pk == 8
    assert document.version_group_id == "vg_keep_me"


def test_list_returns_nested_tree_with_hidden_root_as_container(api, monkeypatch):
    client, _, folders = api
    root = folder(pk=1, folder_id="root", name="/", is_root=True)
    parent = folder(pk=2, folder_id="parent", parent_pk=1, name="Research")
    child = folder(pk=3, folder_id="child", parent_pk=2, name="Notes")

    async def owned_kb(*args, **kwargs):
        return SimpleNamespace(pk=10, id="kb_10", user_id=7)

    async def list_all(*args, **kwargs):
        return [root, parent, child]

    monkeypatch.setattr(folders, "get_knowledge_base_by_id", owned_kb)
    monkeypatch.setattr(folders, "list_folders", list_all)
    response = client.get("/kb/document-folders", params={"knowledge_base_id": "kb_10"})
    assert response.status_code == 200
    assert response.json()["data"] == [
        {
            "id": "parent",
            "parent_id": "root",
            "name": "Research",
            "is_root": False,
            "children": [
                {
                    "id": "child",
                    "parent_id": "parent",
                    "name": "Notes",
                    "is_root": False,
                    "children": [],
                }
            ],
        }
    ]
