from typing import Any

from langchain_core.documents import Document as LCDocument

from clients.vector_store_client import get_vector_store


MetadataFilter = dict[str, int | str]


def build_metadata_filter(
        *,
        user_id: int | None = None,
        knowledge_base_id: str | None = None,
) -> MetadataFilter:
    metadata_filter: MetadataFilter = {}
    if user_id:
        metadata_filter["user_id"] = user_id
    if knowledge_base_id:
        metadata_filter["knowledge_base_id"] = knowledge_base_id
    return metadata_filter



def build_milvus_expr(metadata_filter: MetadataFilter) -> str | None:
    if not metadata_filter:
        return None

    expr_parts: list[str] = []
    for key, value in metadata_filter.items():
        if isinstance(value, str):
            escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
            expr_parts.append(f'{key} == "{escaped_value}"')
        else:
            expr_parts.append(f"{key} == {value}")
    return " and ".join(expr_parts)


async def get_retriever(
        top_k: int = 4,
        *,
        user_id: int | None = None,
        knowledge_base_id: str | None = None,
):
    vector_store = get_vector_store()
    search_kwargs: dict[str, Any] = {"k": top_k}
    metadata_filter = build_metadata_filter(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
    )
    expr = build_milvus_expr(metadata_filter)
    if expr:
        search_kwargs["expr"] = expr

    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs=search_kwargs,
    )

    return retriever


async def retrieve_documents(
        query: str,
        top_k: int = 4,
        *,
        user_id: int | None = None,
        knowledge_base_id: str | None = None,
) -> list[LCDocument]:
    retriever = await get_retriever(
        top_k,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
    )
    return retriever.invoke(query)


async def retrieve_documents_with_scores(
        query: str,
        top_k: int = 4,
        *,
        user_id: int | None = None,
        knowledge_base_id: str | None = None,
):
    vector_store = get_vector_store()
    metadata_filter = build_metadata_filter(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
    )
    expr = build_milvus_expr(metadata_filter)
    search_kwargs: dict[str, Any] = {
        "query": query,
        "k": top_k,
    }
    if expr:
        search_kwargs["expr"] = expr
    return vector_store.similarity_search_with_score(**search_kwargs)



def build_retrieval_result(docs: list[LCDocument]) -> list[dict]:
    results: list[dict] = []
    for doc in docs:
        results.append(
            {
                "knowledge_base_id": doc.metadata.get("knowledge_base_id"),
                "document_id": doc.metadata.get("document_id"),
                "chunk_id": doc.metadata.get("chunk_id"),
                "page_no": doc.metadata.get("page_no"),
                "text": doc.page_content,
            }
        )

    return results












