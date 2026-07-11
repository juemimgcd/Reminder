import asyncio
import re
from functools import lru_cache
from pathlib import Path
from langchain_core.documents import Document as LCDocument

from app.mneme.conf.logging import app_logger
from app.mneme.utils.exceptions import BusinessException


PAGE_BREAK_PATTERN = re.compile(r"\f+")


@lru_cache(maxsize=1)
def build_markitdown_converter():
    try:
        from markitdown import MarkItDown
    except ImportError as exc:
        raise RuntimeError(
            "MarkItDown is not installed. Run `pip install -r requirements.txt` first."
        ) from exc
    return MarkItDown()


def convert_file_to_markdown(file_path: str) -> str:
    converter = build_markitdown_converter()
    result = converter.convert(file_path)

    markdown = getattr(result, "text_content", None)
    if not isinstance(markdown, str):
        markdown = getattr(result, "markdown", None)
    if not isinstance(markdown, str):
        markdown = getattr(result, "text", None)

    if not isinstance(markdown, str) or not markdown.strip():
        raise ValueError("converted markdown is empty")

    return markdown.replace("\r\n", "\n").strip()


def build_langchain_documents_from_markdown(
        *,
        markdown: str,
        file_path: str,
        file_type: str,
        user_id: int,
        knowledge_base_id: str,
        knowledge_base_pk: int,
        document_id: str,
        document_pk: int,
        file_name: str,
) -> list[LCDocument]:
    base_metadata = {
        "user_id": user_id,
        "knowledge_base_id": knowledge_base_id,
        "knowledge_base_pk": knowledge_base_pk,
        "document_id": document_id,
        "document_pk": document_pk,
        "file_name": file_name,
        "file_type": file_type,
        "source": str(file_path),
        "content_format": "markdown",
        "content_converter": "markitdown",
    }

    parts = [part.strip() for part in PAGE_BREAK_PATTERN.split(markdown)] if "\f" in markdown else [markdown]

    docs: list[LCDocument] = []
    page_index = 0
    for part in parts:
        if not part:
            continue
        metadata = dict(base_metadata)
        if len(parts) > 1:
            metadata["page"] = page_index
        docs.append(LCDocument(page_content=part, metadata=metadata))
        page_index += 1

    if not docs:
        raise ValueError("converted markdown is empty")

    return docs


async def load_langchain_documents(
        *,
        file_path: str,
        file_type: str,
        user_id: int,
        knowledge_base_id: str,
        knowledge_base_pk: int,
        document_id: str,
        document_pk: int,
        file_name: str,
) -> list[LCDocument]:
    # {
    #     "user_id": 1,
    #     "knowledge_base_id": "kb_demo_001",
    #     "knowledge_base_pk": 1,
    #     "document_id": "doc_demo_001",
    #     "document_pk": 1,
    #     "file_name": "demo.txt",
    #     "file_type": "txt",
    #     "source": "E:/python_files/agentic_rag/storage/raw/demo.txt",
    # }
    path = Path(file_path)
    if not path.exists():
        app_logger.bind(module="document_loader").warning(
            f"load document failed document_id={document_id} file_path={file_path} reason=file_not_found"
        )
        raise BusinessException(status_code=404,message="file not found")

    app_logger.bind(module="document_loader").info(
        f"load document start document_id={document_id} file_type={file_type} file_name={file_name}"
    )
    try:
        markdown = await asyncio.to_thread(convert_file_to_markdown, str(path))
        docs = build_langchain_documents_from_markdown(
            markdown=markdown,
            file_path=str(path),
            file_type=file_type,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            knowledge_base_pk=knowledge_base_pk,
            document_id=document_id,
            document_pk=document_pk,
            file_name=file_name,
        )
    except RuntimeError as exc:
        app_logger.bind(module="document_loader").exception(
            f"load document failed document_id={document_id} file_path={file_path} reason=markitdown_missing"
        )
        raise BusinessException(message=str(exc), status_code=500) from exc
    except Exception as exc:
        app_logger.bind(module="document_loader").exception(
            f"load document failed document_id={document_id} file_path={file_path} "
            f"file_type={file_type} error_type={type(exc).__name__} error={exc}"
        )
        raise BusinessException(
            message=f"document parse failed: {exc}",
            status_code=400,
        ) from exc

    app_logger.bind(module="document_loader").info(
        f"load document completed document_id={document_id} doc_count={len(docs)}"
    )
    return docs















