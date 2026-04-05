from langchain_core.documents import Document as LCDocument

from utils.vector_store import get_vector_store


def build_metadata_filter(
        *,
        user_id: int | None = None,
        knowledge_base_id: str | None = None,
) -> dict:
    metadata_filter: dict[str, int | str] = {}
    if user_id:
        metadata_filter["user_id"] = user_id
    if knowledge_base_id:
        metadata_filter["knowledge_base_id"] = knowledge_base_id
    return metadata_filter


async def get_retriever(
        top_k: int = 4,
        *,
        user_id: int | None = None,
        knowledge_base_id: str | None = None,
):
    vector_store = get_vector_store()
    search_kwargs = {"k": top_k}
    metadata_filter = build_metadata_filter(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
    )
    if metadata_filter:
        search_kwargs["filter"] = metadata_filter

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
    return vector_store.similarity_search_with_score(
        query=query,
        k=top_k,
        filter=metadata_filter or None,
    )


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


async def get_mmr_retriever(
        top_k: int = 4,
        fetch_k: int = 20,
        *,
        user_id: int | None = None,
        knowledge_base_id: str | None = None,
):
    vector_store = get_vector_store()
    search_kwargs = {
        "k": top_k,
        "fetch_k": fetch_k,
        "lambda_mult": 0.5,
    }
    metadata_filter = build_metadata_filter(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
    )
    if metadata_filter:
        search_kwargs["filter"] = metadata_filter

    retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs=search_kwargs,
    )

    return retriever









