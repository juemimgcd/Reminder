from langchain_core.output_parsers import StrOutputParser

from clients.llm_client import get_llm
from services.context_service import build_query_context
from utils.prompt_builder import get_rag_prompt




async def generate_rag_answer(
        question: str,
        *,
        knowledge_base_id: str,
        user_id: int | None = None,
        top_k: int = 4,
) -> dict:
    context_packet = await build_query_context(
        query=question,
        top_k=top_k,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
    )

    if not context_packet["sources"]:
        return {
            "answer": "我无法从已检索内容中找到相关答案。请先确认文档已经完成索引。",
            "sources": [],
        }

    prompt = get_rag_prompt()
    llm = get_llm()
    chain = prompt | llm | StrOutputParser()

    answer = await chain.ainvoke(
        {
            "context": context_packet["context_text"],
            "question": question,
        }
    )

    return {
        "answer": answer,
        "sources": context_packet["sources"],
    }













