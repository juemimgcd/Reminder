import asyncio
from pathlib import Path
from langchain_core.documents import Document as LCDocument
from langchain_community.document_loaders import PyPDFLoader, TextLoader

from utils.exceptions import BusinessException


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

    path = Path(file_path)
    if not path.exists():
        raise BusinessException(status_code=404,message="file not found")

    loader = None
    if file_type == "pdf":
        loader = PyPDFLoader(str(file_path))

    elif file_type in ["txt","md"]:
        loader = TextLoader(file_path,autodetect_encoding=True)
    else:
        raise BusinessException(message="Incorrect file type")

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

    return docs















