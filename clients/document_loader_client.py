import asyncio
from pathlib import Path
from langchain_core.documents import Document as LCDocument
from langchain_community.document_loaders import PyPDFLoader, TextLoader

from conf.logging import app_logger
from utils.exceptions import BusinessException


# 读取原始文件并补齐文档域流水线后续步骤需要的基础 metadata。
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
    # 每个 loader 产出的 doc.metadata 最终会补成类似：
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

    loader = None
    if file_type == "pdf":
        loader = PyPDFLoader(str(file_path))

    elif file_type in ["txt","md"]:
        loader = TextLoader(file_path,autodetect_encoding=True)
    else:
        raise BusinessException(message="Incorrect file type")

    app_logger.bind(module="document_loader").info(
        f"load document start document_id={document_id} file_type={file_type} file_name={file_name}"
    )
    docs = await asyncio.to_thread(loader.load)

    for doc in docs:
        doc.metadata["user_id"] = user_id
        doc.metadata["knowledge_base_id"] = knowledge_base_id
        doc.metadata["knowledge_base_pk"] = knowledge_base_pk
        doc.metadata["document_id"] = document_id
        doc.metadata["document_pk"] = document_pk
        doc.metadata["file_name"] = file_name
        doc.metadata["file_type"] = file_type
        doc.metadata["source"] = str(file_path)

    app_logger.bind(module="document_loader").info(
        f"load document completed document_id={document_id} doc_count={len(docs)}"
    )
    return docs















