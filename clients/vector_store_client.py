import json
from typing import Any

from langchain_core.documents import Document as LCDocument
from langchain_milvus import Milvus

from conf.config import settings
from clients.embedding_client import get_embeddings


def _build_connection_args() -> dict[str, str]:
    connection_args: dict[str, str] = {
        "uri": settings.MILVUS_URI,
        "db_name": settings.MILVUS_DB_NAME,
    }
    if settings.MILVUS_TOKEN:
        connection_args["token"] = settings.MILVUS_TOKEN
    return connection_args



def _build_search_params() -> dict[str, Any]:
    try:
        parsed = json.loads(settings.MILVUS_SEARCH_PARAMS)
    except json.JSONDecodeError:
        parsed = {}

    if isinstance(parsed, dict):
        return parsed
    return {}



def _build_index_params() -> dict[str, Any]:
    search_params = _build_search_params()
    metric_type = search_params.get("metric_type", settings.MILVUS_METRIC_TYPE)
    return {
        "index_type": settings.MILVUS_INDEX_TYPE,
        "metric_type": metric_type,
    }



def get_vector_store() -> Milvus:
    return Milvus(
        embedding_function=get_embeddings(),
        connection_args=_build_connection_args(),
        collection_name=settings.MILVUS_COLLECTION_NAME,
        index_params=_build_index_params(),
        search_params=_build_search_params(),
        consistency_level=settings.MILVUS_CONSISTENCY_LEVEL,
        auto_id=False,
        primary_field="pk",
        text_field="text",
        vector_field="vector",
        drop_old=settings.MILVUS_DROP_OLD,
    )


async def add_documents_to_vector_store(chunk_docs: list[LCDocument]) -> None:
    if not chunk_docs:
        return

    vector_store = get_vector_store()
    ids = [str(chunk.metadata["chunk_id"]) for chunk in chunk_docs]
    vector_store.add_documents(documents=chunk_docs, ids=ids)


async def delete_documents_from_vector_store(*, ids: list[str] | None = None) -> None:
    if not ids:
        return

    vector_store = get_vector_store()
    vector_store.delete(ids=ids)


async def drop_vector_collection() -> None:
    vector_store = get_vector_store()
    vector_store.drop()

