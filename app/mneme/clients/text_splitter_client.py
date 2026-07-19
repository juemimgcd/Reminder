import re
import uuid
from dataclasses import dataclass
from typing import Any, cast

from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.mneme.conf.logging import app_logger

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


@dataclass
class SectionBlock:
    section_id: str
    section_title: str | None
    section_level: int | None
    section_path: str | None
    section_summary: str | None
    section_start_offset: int
    page_no: int | None
    text: str
    base_metadata: dict[str, Any]


async def build_text_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", "\u3002", "\uff1b", "\uff0c", "\u3001", " ", ""],
        add_start_index=True,
    )


def build_section_summary(*, title: str | None, text: str, max_chars: int = 120) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        return title or ""

    if len(normalized) > max_chars:
        normalized = f"{normalized[:max_chars].rstrip()}..."

    return f"{title}: {normalized}" if title else normalized


def _build_section_block(
    *,
    document_id: str,
    section_index: int,
    title: str | None,
    level: int | None,
    path: str | None,
    start_offset: int,
    page_no: int | None,
    text: str,
    base_metadata: dict[str, Any],
) -> SectionBlock | None:
    section_text = text.strip()
    if not section_text:
        return None

    return SectionBlock(
        section_id=f"{document_id}_sec_{section_index}",
        section_title=title,
        section_level=level,
        section_path=path,
        section_summary=build_section_summary(title=title, text=section_text),
        section_start_offset=start_offset,
        page_no=page_no,
        text=section_text,
        base_metadata=base_metadata,
    )


def split_document_into_sections(doc: LCDocument) -> list[SectionBlock]:
    text = doc.page_content.replace("\r\n", "\n").strip()
    if not text:
        return []

    matches = list(HEADING_PATTERN.finditer(text))
    raw_page = doc.metadata.get("page")
    page_no = raw_page + 1 if isinstance(raw_page, int) else None
    base_metadata = cast(dict[str, Any], dict(doc.metadata))
    document_id = str(doc.metadata.get("document_id") or "document")

    if not matches:
        section = _build_section_block(
            document_id=document_id,
            section_index=0,
            title=None,
            level=None,
            path=None,
            start_offset=0,
            page_no=page_no,
            text=text,
            base_metadata=base_metadata,
        )
        return [section] if section else []

    sections: list[SectionBlock] = []
    section_index = 0

    first_heading_start = matches[0].start()
    if first_heading_start > 0:
        preamble = _build_section_block(
            document_id=document_id,
            section_index=section_index,
            title=None,
            level=None,
            path=None,
            start_offset=0,
            page_no=page_no,
            text=text[:first_heading_start],
            base_metadata=base_metadata,
        )
        if preamble:
            sections.append(preamble)
            section_index += 1

    heading_stack: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        level = len(match.group(1))
        title = match.group(2).strip()
        heading_stack = heading_stack[: level - 1] + [title]
        section_path = " > ".join(heading_stack)
        section = _build_section_block(
            document_id=document_id,
            section_index=section_index,
            title=title,
            level=level,
            path=section_path,
            start_offset=start,
            page_no=page_no,
            text=text[start:end],
            base_metadata=base_metadata,
        )
        if not section:
            continue
        sections.append(section)
        section_index += 1

    return sections


async def split_documents(
    *,
    document_id: str,
    documents: list[LCDocument],
) -> list[LCDocument]:
    app_logger.bind(module="text_splitter").info(
        f"split documents start document_id={document_id} source_doc_count={len(documents)}"
    )
    splitter = await build_text_splitter()
    chunks: list[LCDocument] = []
    global_chunk_index = 0

    for source_doc in documents:
        for section in split_document_into_sections(source_doc):
            section_doc = LCDocument(
                page_content=section.text,
                metadata={
                    **section.base_metadata,
                    "section_id": section.section_id,
                    "section_title": section.section_title,
                    "section_level": section.section_level,
                    "section_path": section.section_path,
                    "section_summary": section.section_summary,
                },
            )
            section_chunks = splitter.split_documents([section_doc])
            for section_chunk_index, chunk in enumerate(section_chunks):
                local_start = chunk.metadata.get("start_index")
                absolute_start = (
                    section.section_start_offset + local_start
                    if isinstance(local_start, int)
                    else None
                )
                raw_page = chunk.metadata.get("page")
                page_no = raw_page + 1 if isinstance(raw_page, int) else section.page_no

                chunk.metadata["chunk_id"] = f"{document_id}_chunk_{global_chunk_index}_{uuid.uuid4().hex[:6]}"
                chunk.metadata["chunk_index"] = global_chunk_index
                chunk.metadata["section_id"] = section.section_id
                chunk.metadata["section_title"] = section.section_title
                chunk.metadata["section_level"] = section.section_level
                chunk.metadata["section_path"] = section.section_path
                chunk.metadata["section_summary"] = section.section_summary
                chunk.metadata["section_chunk_index"] = section_chunk_index
                chunk.metadata["page_no"] = page_no
                chunk.metadata["start_offset"] = absolute_start
                chunks.append(chunk)
                global_chunk_index += 1

    app_logger.bind(module="text_splitter").info(
        f"split documents completed document_id={document_id} chunk_count={len(chunks)}"
    )
    return chunks
