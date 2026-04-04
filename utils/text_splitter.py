import uuid

from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter


async def build_text_splitter() -> RecursiveCharacterTextSplitter:

    return RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
        add_start_index=True

    )


async def split_documents(
        *,
        document_id: str,
        documents: list[LCDocument],
) -> list[LCDocument]:

    splitter = await build_text_splitter()
    chunks = splitter.split_documents(documents=documents)

    for index,chunk in enumerate(chunks):
        raw_page = chunk.metadata.get("page")
        page_no = raw_page + 1 if isinstance(raw_page,int) else None

        start_offset = chunk.metadata.get("start_index")

        chunk.metadata["chunk_id"] = f"{document_id}_chunk_{index}_{uuid.uuid4().hex[:6]}"
        chunk.metadata["chunk_index"] = index
        chunk.metadata["page_no"] = page_no
        chunk.metadata["start_offset"] = start_offset

    return chunks












