import uuid

from langchain_core.documents import Document as LCDocument
from langchain_core.output_parsers import PydanticOutputParser

from schemas.memory_entry import MemoryEntryExtractionResult
from utils.entry_prompt import get_entry_extraction_prompt
from utils.llm import get_llm


async def extract_entries_from_chunk(doc: LCDocument) -> list[dict]:
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
                "document_id": doc.metadata.get("document_id"),
                "chunk_id": doc.metadata.get("chunk_id"),
                "page_no": doc.metadata.get("page_no"),
                "entry_name": item.entry_name,
                "entry_type": item.entry_type,
                "summary": item.summary,
                "evidence_text": item.evidence_text,
                "importance_score": item.importance_score,
            }
        )
    return entries





async def extract_entries_from_chunks(chunk_docs: list[LCDocument]) -> list[dict]:
    entries: list[dict] = []
    for chunk in chunk_docs:
        chunk_entries = await extract_entries_from_chunk(chunk)
        entries.extend(chunk_entries)

    return entries






