from langchain_core.documents import Document as LCDocument
from langchain_core.output_parsers import StrOutputParser

from clients.llm_client import get_llm
from utils.prompt_builder import get_rag_prompt
from services.context_service import retrieve_documents


def format_docs(docs: list[LCDocument]) -> str:
    sections: list[str] = []

    for index, doc in enumerate(docs, start=1):
        sections.append(
            "\n".join(
                [
                    f"[片段 {index}]",
                    f"knowledge_base_id={doc.metadata.get('knowledge_base_id')}",
                    f"document_id={doc.metadata.get('document_id')}",
                    f"chunk_id={doc.metadata.get('chunk_id')}",
                    f"page_no={doc.metadata.get('page_no')}",
                    f"text={doc.page_content}",

                ]
            )
        )

    return "\n\n".join(sections)




def build_sources(docs: list[LCDocument]) -> list[dict]:
    sources: list[dict] = []
    for doc in docs:
        sources.append(
            {
                "knowledge_base_id": doc.metadata.get("knowledge_base_id"),
                "document_id": doc.metadata.get("document_id"),
                "chunk_id": doc.metadata.get("chunk_id"),
                "page_no": doc.metadata.get("page_no"),
                "text": doc.page_content,
            }
        )

    return sources




async def generate_rag_answer(
        question: str,
        *,
        knowledge_base_id: str,
        user_id: int | None = None,
        top_k: int = 4,
) -> dict:

    docs = await retrieve_documents(
        query=question,
        top_k=top_k,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
    )
    if not docs:
        return {
            "answer": "我无法从已检索内容中找到相关答案。请先确认文档已经完成索引。",
            "sources": [],
        }

    context = format_docs(docs=docs)
    prompt = get_rag_prompt()
    llm = get_llm()
    chain = prompt | llm | StrOutputParser()

    answer = await chain.ainvoke(
        {
            "context": context,
            "question": question,
        }
    )

    return {
        "answer": answer,
        "sources": build_sources(docs=docs),
    }














