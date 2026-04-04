from pathlib import Path
from fastapi import HTTPException
from langchain_core.documents import Document as LCDocument
from langchain_community.document_loaders import PyPDFLoader, TextLoader

from utils.exceptions import BusinessException


async def load_langchain_documents(
        *,
        file_path: str,
        file_type: str,
        document_id: str,
        file_name: str,
) -> list[LCDocument]:

    file_path = Path(file_path)
    if not file_path.exists():
        raise BusinessException(status_code=404,message="file not found")

    loader = None
    if file_type == "pdf":
        loader = PyPDFLoader(str(file_path))

    elif file_type in ["txt","md"]:
        loader = TextLoader(file_path,autodetect_encoding=True)
    else:
        raise BusinessException(message="Incorrect file type")

    docs = loader.load()

    for doc in docs:
        doc.metadata["document_id"] = document_id
        doc.metadata["file_name"] = file_name
        doc.metadata["file_type"] = file_type
        doc.metadata["source"] = str(file_path)

    return docs















