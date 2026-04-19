import uuid
from collections import defaultdict
from langchain_core.documents import Document as LCDocument
from langchain_core.output_parsers import PydanticOutputParser
from clients.llm_client import get_llm
from conf.logging import log_event
from schemas.memory_entry import MemoryEntryExtractionResult
from utils.entry_prompt import get_entry_extraction_prompt


def group_entries_by_type(entries: list[dict]) -> dict[str, list[str]]:
    grouped: defaultdict[str, list[str]] = defaultdict(list)

    for item in entries:
        grouped[item["entry_type"]].append(item["entry_name"])

    return dict(grouped)


def build_timeline(entries: list[dict]) -> list[dict]:
    sorted_entries = sorted(entries, key=lambda x: x["created_at"])

    return [
        {
            "entry_id": item["id"],
            "entry_name": item["entry_name"],
            "entry_type": item["entry_type"],
            "summary": item["summary"],
            "created_at": item["created_at"],
        }
        for item in sorted_entries
    ]


def build_theme_groups(entries: list[dict]) -> list[dict]:
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for item in entries:
        grouped[item["entry_name"]].append(item["summary"])

    result: list[dict] = []

    for theme_name,related_entries in grouped.items():
        result.append(
            {
                "theme_name": theme_name,
                "entries": related_entries,
                "count": len(related_entries),
            }
        )

    return sorted(result, key=lambda x: x["count"], reverse=True)



def build_memory_library(entries: list[dict]) -> dict:
    return {
        "timeline": build_timeline(entries),
        "by_type": group_entries_by_type(entries),
        "by_theme": build_theme_groups(entries),
    }






async def extract_entries_from_chunk(doc: LCDocument) -> list[dict]:
    log_event(
        "memory_service",
        "debug",
        "memory.extract_chunk.start",
        document_id=doc.metadata.get("document_id"),
        chunk_id=doc.metadata.get("chunk_id"),
    )
    parser = PydanticOutputParser(pydantic_object=MemoryEntryExtractionResult)
    instructions = parser.get_format_instructions()

    prompt = get_entry_extraction_prompt(format_instructions=instructions)
    llm = get_llm()

    chain = prompt | llm | parser
    result = await chain.ainvoke(
        {
            "document_id": doc.metadata.get("document_id"),
            "chunk_id": doc.metadata.get("chunk_id"),
            "page_no": doc.metadata.get("page_no"),
            "chunk_text": doc.page_content,
        }
    )

    entries: list[dict] = []

    for item in result.entries:
        entries.append(
            {
                "id": f"entry_{uuid.uuid4().hex[:12]}",
                "user_id": doc.metadata.get("user_id"),
                "knowledge_base_id": doc.metadata.get("knowledge_base_id"),
                "knowledge_base_pk": doc.metadata.get("knowledge_base_pk"),
                "document_id": doc.metadata.get("document_id"),
                "document_pk": doc.metadata.get("document_pk"),
                "chunk_id": doc.metadata.get("chunk_id"),
                "page_no": doc.metadata.get("page_no"),
                "entry_name": item.entry_name,
                "entry_type": item.entry_type,
                "summary": item.summary,
                "evidence_text": item.evidence_text,
                "importance_score": item.importance_score,
            }
        )

    log_event(
        "memory_service",
        "debug",
        "memory.extract_chunk.completed",
        document_id=doc.metadata.get("document_id"),
        chunk_id=doc.metadata.get("chunk_id"),
        entry_count=len(entries),
    )
    return entries





async def extract_entries_from_chunks(chunk_docs: list[LCDocument]) -> list[dict]:
    log_event(
        "memory_service",
        "info",
        "memory.extract_batch.start",
        chunk_count=len(chunk_docs),
    )
    entries: list[dict] = []
    for chunk in chunk_docs:
        chunk_entries = await extract_entries_from_chunk(chunk)
        entries.extend(chunk_entries)

    log_event(
        "memory_service",
        "info",
        "memory.extract_batch.completed",
        chunk_count=len(chunk_docs),
        total_entry_count=len(entries),
    )
    return entries




