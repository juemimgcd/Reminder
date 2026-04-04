from langchain_core.documents import Document as LCDocument
from langchain_core.output_parsers import StrOutputParser

from utils.llm import get_llm
from utils.prompt_builder import get_rag_prompt
from utils.retriever import retrieve_documents


async def format_docs(docs: list[LCDocument]) -> str:

    section:list[str] = []

    for index,doc in enumerate(docs):
        section.append(
            "\n".join(
                [
                    f"[片段 {index}]",
                    f"document_id={doc.metadata.get('document_id')}",
                    f"chunk_id={doc.metadata.get('chunk_id')}",
                    f"page_no={doc.metadata.get('page_no')}",
                    f"text={doc.page_content}",

                ]
            )
        )

    return "\n\n".join(section)




async def build_sources(docs: list[LCDocument]) -> list[dict]:

    sources:list[dict] = []
    for index,doc in enumerate(docs):
        sources.append(
            {
                "document_id": doc.metadata.get("document_id"),
                "chunk_id": doc.metadata.get("chunk_id"),
                "page_no": doc.metadata.get("page_no"),
                "text": doc.page_content,
            }
        )

    return sources




async def generate_rag_answer(question: str, top_k: int = 4) -> dict:

    res = await retrieve_documents(query=question,top_k=top_k)
    if not res:
        return {
            "answer": "我无法从已检索内容中找到相关答案。请先确认文档已经完成索引。",
            "sources": [],
        }

    context = await format_docs(docs=res)
    prompt = await get_rag_prompt()
    llm = get_llm()
    chain = prompt | llm | StrOutputParser()

    answer = await chain.ainvoke(
        {
            "context":context,
            "question":question
        }
    )

    return {
        "answer":answer,
        "sources":await build_sources(docs=res)
    }














