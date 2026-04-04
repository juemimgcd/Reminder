from langchain_core.documents import Document as LCDocument
from langchain_chroma import Chroma

from conf.config import settings
from utils.embeddings import get_embeddings


def get_vector_store() -> Chroma:
    return Chroma(
        collection_name=settings.CHROMA_COLLECTION_NAME,
        persist_directory=settings.CHROMA_PERSIST_DIR,
        embedding_function=get_embeddings(),
    )


async def add_documents_to_vector_store(chunk_docs: list[LCDocument]) -> None:
    vector_store = get_vector_store()
    ids = [chunk.metadata["chunk_id"] for chunk in chunk_docs]
    vector_store.add_documents(documents=chunk_docs, ids=ids)
