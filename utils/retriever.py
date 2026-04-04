from langchain_core.documents import Document as LCDocument

from utils.vector_store import get_vector_store


async def get_retriever(top_k: int = 4):
    vector_store = await get_vector_store()
    retriever = vector_store.as_retriever(
        search_kwargs={"k": top_k}
    )

    return retriever



async def retrieve_documents(query: str, top_k: int = 4) -> list[LCDocument]:
    retriever = await get_retriever(top_k)
    result = retriever.invoke(query)
    return result


async def retrieve_documents_with_scores(query: str, top_k: int = 4):
    vector_store = await get_vector_store()
    return vector_store.similarity_search_with_vectors(query=query, k=top_k)


async def build_retrieval_result(docs: list[LCDocument]) -> list[dict]:

    results: list[dict] = []
    for doc in docs:
        results.append(
            {
                "document_id": doc.metadata.get("document_id"),
                "chunk_id": doc.metadata.get("chunk_id"),
                "page_no": doc.metadata.get("page_no"),
                "text": doc.page_content,
            }
        )

    return results


async def get_mmr_retriever(top_k: int = 4, fetch_k: int = 20):

    vector_store = await get_vector_store()
    retrieve = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": top_k,
            "fetch_k":fetch_k,
            "lambda_mult":0.5
        }
    )

    return retrieve









