import uuid

from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from conf.logging import app_logger

# 构建当前项目统一使用的文本切分器配置。
async def build_text_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
        add_start_index=True

    )



# 将原始文档切成 chunk，并补齐 chunk 级 metadata。
async def split_documents(
        *,
        document_id: str,
        documents: list[LCDocument],
) -> list[LCDocument]:
    # 每个 chunk.metadata 最终会补成类似：
    # {
    #     "chunk_id": "doc_demo_001_chunk_0_a1b2c3",
    #     "chunk_index": 0,
    #     "page_no": 1,
    #     "start_offset": 0,
    #     ...
    # }
    app_logger.bind(module="text_splitter").info(
        f"split documents start document_id={document_id} source_doc_count={len(documents)}"
    )
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

    app_logger.bind(module="text_splitter").info(
        f"split documents completed document_id={document_id} chunk_count={len(chunks)}"
    )
    return chunks












