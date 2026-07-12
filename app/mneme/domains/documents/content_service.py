import asyncio
import html
import re
import unicodedata
from pathlib import Path
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.clients.document_loader_client import convert_file_to_markdown
from app.mneme.models.document import Document
from app.mneme.schemas.document import DocumentContentData, DocumentContentSection
from app.mneme.utils.exceptions import BusinessException


RenderMode = Literal["markdown", "text", "structured", "office", "pdf", "unsupported"]

MARKDOWN_TYPES = {"md", "markdown"}
TEXT_TYPES = {"txt"}
STRUCTURED_TYPES = {"json", "csv", "xml", "html", "htm"}
OFFICE_TYPES = {"doc", "docx", "ppt", "pptx", "xls", "xlsx", "epub"}
MIME_TYPES = {
    "md": "text/markdown",
    "markdown": "text/markdown",
    "txt": "text/plain",
    "json": "application/json",
    "csv": "text/csv",
    "xml": "application/xml",
    "html": "text/plain",
    "htm": "text/plain",
    "pdf": "application/pdf",
}
DECODE_WARNING = "Unable to decode document as UTF-8 or UTF-8-SIG. Download the original file to read it."
PARSE_WARNING = "Unable to parse document content. Download the original file to read it."
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def normalize_file_type(file_type: str) -> str:
    return file_type.strip().lower().lstrip(".")


def classify_render_mode(file_type: str) -> RenderMode:
    normalized = normalize_file_type(file_type)
    if normalized in MARKDOWN_TYPES:
        return "markdown"
    if normalized in TEXT_TYPES:
        return "text"
    if normalized in STRUCTURED_TYPES:
        return "structured"
    if normalized in OFFICE_TYPES:
        return "office"
    if normalized == "pdf":
        return "pdf"
    return "unsupported"


def sanitize_download_name(file_name: str) -> str:
    basename = file_name.replace("\\", "/").rsplit("/", 1)[-1]
    sanitized = "".join(
        character
        for character in basename
        if character not in {"\r", "\n"} and not unicodedata.category(character).startswith("C")
    )
    sanitized = sanitized.replace(":", "_").strip().strip(".")
    return sanitized[:255] or "document"


def require_source_file(document: Document) -> Path:
    path = Path(document.file_path)
    if not path.is_file():
        raise BusinessException(
            message="document source file is unavailable",
            code=4046,
            status_code=404,
        )
    return path


def read_text_safely(path: Path) -> tuple[str | None, str | None, str | None]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            text = raw.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")
            return text, encoding, None
        except UnicodeDecodeError:
            continue
    return None, None, DECODE_WARNING


def neutralize_embedded_html(text: str) -> str:
    return html.escape(text, quote=True)


def split_sections(markdown: str) -> list[DocumentContentSection]:
    sections: list[DocumentContentSection] = []
    title: str | None = None
    body: list[str] = []

    def append_current() -> None:
        content = "\n".join(body).strip()
        if title is not None or content:
            sections.append(DocumentContentSection(title=title, text=content))

    for line in markdown.splitlines():
        match = HEADING_PATTERN.match(line)
        if match:
            append_current()
            title = match.group(2).strip()
            body = []
        else:
            body.append(line)
    append_current()
    return sections


def content_mime_type(file_type: str, mode: RenderMode) -> str:
    normalized = normalize_file_type(file_type)
    if mode == "office":
        return "text/markdown"
    return MIME_TYPES.get(normalized, "application/octet-stream")


async def build_document_content(
    document: Document,
    *,
    folder_id: str,
) -> DocumentContentData:
    path = require_source_file(document)
    mode = classify_render_mode(document.file_type)
    mime_type = content_mime_type(document.file_type, mode)
    text: str | None = None
    sections: list[DocumentContentSection] = []
    parse_warning: str | None = None

    if mode == "pdf" or mode == "unsupported":
        pass
    elif mode in {"markdown", "text", "structured"}:
        text, _encoding, parse_warning = await asyncio.to_thread(read_text_safely, path)
        if text is not None and normalize_file_type(document.file_type) in {"md", "markdown", "html", "htm"}:
            text = neutralize_embedded_html(text)
    elif mode == "office":
        try:
            text = await asyncio.to_thread(convert_file_to_markdown, str(path))
            text = neutralize_embedded_html(text)
            sections = split_sections(text)
        except Exception:
            text = None
            parse_warning = PARSE_WARNING

    return DocumentContentData(
        document_id=document.id,
        folder_id=folder_id,
        file_name=document.file_name,
        render_mode=mode,
        mime_type=mime_type,
        text=text,
        sections=sections,
        parse_warning=parse_warning,
    )


async def list_document_versions(
    db: AsyncSession,
    *,
    version_group_id: str,
    user_id: int,
) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(
            Document.user_id == user_id,
            Document.version_group_id == version_group_id,
        )
        .order_by(
            Document.version_number.desc(),
            Document.created_at.desc(),
            Document.pk.desc(),
        )
    )
    return list(result.scalars().all())
