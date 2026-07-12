import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.mneme.conf.database import get_database
from app.mneme.domains.documents.content_service import (
    build_document_content,
    classify_render_mode,
    read_text_safely,
    sanitize_download_name,
)
from app.mneme.domains.documents.router import router
from app.mneme.utils.auth import get_current_user
from app.mneme.utils.exceptions import BusinessException, business_exception_handler


def document(
    raw_path: Path,
    *,
    document_id: str = "doc_owner",
    owner_id: int = 7,
    file_name: str = "notes.md",
    file_type: str = "md",
    version_group_id: str = "vg_notes",
    version_number: int = 1,
    created_at: datetime | None = None,
):
    return SimpleNamespace(
        pk=11,
        id=document_id,
        user_id=owner_id,
        knowledge_base_id="kb_owner",
        knowledge_base_pk=13,
        folder_pk=17,
        file_name=file_name,
        file_path=str(raw_path),
        file_type=file_type,
        file_size=raw_path.stat().st_size if raw_path.exists() else 0,
        status="indexed",
        version_group_id=version_group_id,
        version_number=version_number,
        created_at=created_at or datetime(2026, 7, 12, tzinfo=UTC),
    )


@pytest.fixture
def content_api(monkeypatch, tmp_path):
    import app.mneme.domains.documents.router as documents_router

    raw = tmp_path / "stored"
    raw.write_text("# Complete\n\nA complete document.", encoding="utf-8")
    owned = document(raw)
    records = {owned.id: owned}

    async def get_owned(_db, document_id, *, user_id=None, knowledge_base_pk=None):
        candidate = records.get(document_id)
        if candidate is None or candidate.user_id != user_id:
            return None
        return candidate

    async def get_folder(_db, *, folder_pk, user_id):
        if folder_pk == 17 and user_id == 7:
            return SimpleNamespace(pk=17, id="fld_notes", user_id=7)
        return None

    monkeypatch.setattr(documents_router, "get_document_by_id", get_owned)
    monkeypatch.setattr(documents_router, "get_folder_by_pk", get_folder)

    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(BusinessException, business_exception_handler)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
    app.dependency_overrides[get_database] = lambda: SimpleNamespace()

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, records, owned, documents_router, tmp_path


def test_render_modes_are_explicit():
    assert classify_render_mode("md") == "markdown"
    assert classify_render_mode("pdf") == "pdf"
    assert classify_render_mode("docx") == "office"
    assert classify_render_mode("json") == "structured"
    assert classify_render_mode(".SVG") == "unsupported"


def test_download_name_removes_header_controls_and_path_components():
    assert sanitize_download_name('report\r\nX-Test: injected.pdf') == "reportX-Test_ injected.pdf"
    assert sanitize_download_name("../folder\\secret\x00.txt") == "secret.txt"


def test_read_text_uses_only_utf8_and_returns_a_clear_warning(tmp_path):
    invalid = tmp_path / "legacy.txt"
    invalid.write_bytes(b"\xff\xfeunsafe")

    text, encoding, warning = read_text_safely(invalid)

    assert text is None
    assert encoding is None
    assert warning == "Unable to decode document as UTF-8 or UTF-8-SIG. Download the original file to read it."


def test_owner_can_read_complete_markdown_with_exact_schema(content_api):
    client, _, _, _, _ = content_api

    response = client.get("/kb/documents/doc_owner/content")

    assert response.status_code == 200
    data = response.json()["data"]
    assert set(data) == {
        "document_id",
        "folder_id",
        "file_name",
        "render_mode",
        "mime_type",
        "text",
        "sections",
        "parse_warning",
    }
    assert data == {
        "document_id": "doc_owner",
        "folder_id": "fld_notes",
        "file_name": "notes.md",
        "render_mode": "markdown",
        "mime_type": "text/markdown",
        "text": "# Complete\n\nA complete document.",
        "sections": [],
        "parse_warning": None,
    }


@pytest.mark.parametrize("suffix", ["content", "raw", "versions"])
def test_cross_user_document_is_indistinguishable_from_missing(content_api, suffix):
    client, records, _, _, tmp_path = content_api
    other_path = tmp_path / "other.pdf"
    other_path.write_bytes(b"%PDF-other")
    records["doc_other"] = document(
        other_path,
        document_id="doc_other",
        owner_id=99,
        file_name="other.pdf",
        file_type="pdf",
    )

    response = client.get(f"/kb/documents/doc_other/{suffix}")

    assert response.status_code == 404
    assert response.json()["message"] == "document not found or not owned by current user"


@pytest.mark.parametrize("suffix", ["content", "raw"])
def test_missing_raw_file_returns_controlled_api_error(content_api, suffix):
    client, records, _, _, tmp_path = content_api
    records["doc_missing"] = document(
        tmp_path / "missing.pdf",
        document_id="doc_missing",
        file_name="missing.pdf",
        file_type="pdf",
    )

    response = client.get(f"/kb/documents/doc_missing/{suffix}")

    assert response.status_code == 404
    assert response.json()["message"] == "document source file is unavailable"
    assert "missing.pdf" not in response.text


def test_pdf_may_be_inline_with_pdf_media_type(content_api):
    client, records, _, _, tmp_path = content_api
    pdf_path = tmp_path / "stored-pdf"
    pdf_path.write_bytes(b"%PDF-safe")
    records["doc_pdf"] = document(
        pdf_path,
        document_id="doc_pdf",
        file_name="paper.pdf",
        file_type="pdf",
    )

    response = client.get("/kb/documents/doc_pdf/raw?disposition=inline")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline;")
    assert response.content == b"%PDF-safe"


def test_pdf_honors_explicit_attachment_disposition(content_api):
    client, records, _, _, tmp_path = content_api
    pdf_path = tmp_path / "stored-download-pdf"
    pdf_path.write_bytes(b"%PDF-download")
    records["doc_pdf_download"] = document(
        pdf_path,
        document_id="doc_pdf_download",
        file_name="paper.pdf",
        file_type="pdf",
    )

    response = client.get("/kb/documents/doc_pdf_download/raw?disposition=attachment")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("attachment;")


def test_pdf_content_returns_reader_metadata_without_eager_file_body(content_api):
    client, records, _, _, tmp_path = content_api
    pdf_path = tmp_path / "stored-content-pdf"
    pdf_path.write_bytes(b"%PDF-reader")
    records["doc_pdf_content"] = document(
        pdf_path,
        document_id="doc_pdf_content",
        file_name="reader.pdf",
        file_type="pdf",
    )

    response = client.get("/kb/documents/doc_pdf_content/content")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["render_mode"] == "pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["text"] is None
    assert data["sections"] == []


@pytest.mark.parametrize(
    ("file_name", "file_type", "body"),
    [
        ("page.html", "html", b"<script>alert(1)</script>"),
        ("image.svg", "svg", b"<svg onload='alert(1)'></svg>"),
        ("payload.exe", "exe", b"MZ"),
    ],
)
def test_non_pdf_raw_is_always_binary_attachment(content_api, file_name, file_type, body):
    client, records, _, _, tmp_path = content_api
    path = tmp_path / f"stored-{file_type}"
    path.write_bytes(body)
    records["doc_untrusted"] = document(
        path,
        document_id="doc_untrusted",
        file_name=file_name,
        file_type=file_type,
    )

    response = client.get("/kb/documents/doc_untrusted/raw?disposition=inline")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.content == body


def test_html_content_is_escaped_and_never_returned_as_executable_markup(content_api):
    client, records, _, _, tmp_path = content_api
    html_path = tmp_path / "stored-html"
    html_path.write_text('<img src=x onerror="alert(1)"><script>alert(2)</script>', encoding="utf-8")
    records["doc_html"] = document(
        html_path,
        document_id="doc_html",
        file_name="page.html",
        file_type="html",
    )

    response = client.get("/kb/documents/doc_html/content")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["render_mode"] == "structured"
    assert data["mime_type"] == "text/plain"
    assert "<script" not in data["text"]
    assert "onerror=\"" not in data["text"]
    assert "&lt;script&gt;" in data["text"]


def test_office_conversion_runs_via_asyncio_to_thread(monkeypatch, tmp_path):
    import app.mneme.domains.documents.content_service as service

    office_path = tmp_path / "stored-docx"
    office_path.write_bytes(b"docx")
    calls = []

    def fake_convert(path):
        assert path == str(office_path)
        return "# Overview\nBody\n## Details\nMore"

    async def capture_to_thread(function, *args):
        calls.append((function, args))
        return function(*args)

    monkeypatch.setattr(service, "convert_file_to_markdown", fake_convert)
    monkeypatch.setattr(service.asyncio, "to_thread", capture_to_thread)

    result = asyncio.run(
        build_document_content(
            document(
                office_path,
                document_id="doc_office",
                file_name="brief.docx",
                file_type="docx",
            ),
            folder_id="fld_notes",
        )
    )

    assert calls == [(fake_convert, (str(office_path),))]
    assert result.render_mode == "office"
    assert [section.title for section in result.sections] == ["Overview", "Details"]


def test_versions_are_owner_scoped_same_group_and_newest_first(content_api, monkeypatch):
    client, _, owned, documents_router, _ = content_api
    newer = document(
        Path(owned.file_path),
        document_id="doc_v2",
        version_number=2,
        created_at=owned.created_at + timedelta(days=1),
    )
    observed = {}

    async def list_versions(_db, *, version_group_id, user_id):
        observed.update(version_group_id=version_group_id, user_id=user_id)
        return [newer, owned]

    monkeypatch.setattr(documents_router, "list_document_versions", list_versions)

    response = client.get("/kb/documents/doc_owner/versions")

    assert response.status_code == 200
    assert observed == {"version_group_id": "vg_notes", "user_id": 7}
    data = response.json()["data"]
    assert set(data) == {"items", "total"}
    assert [item["document_id"] for item in data["items"]] == ["doc_v2", "doc_owner"]
    assert [item["version_number"] for item in data["items"]] == [2, 1]
    assert data["total"] == 2
