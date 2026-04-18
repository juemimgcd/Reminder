from langchain_core.output_parsers import StrOutputParser

from clients.llm_client import get_llm
from conf.config import settings
from infra.circuit_breaker import before_call, record_success, record_failure
from infra.retry import retry_async
from services.context_service import build_query_context
from utils.prompt_builder import get_rag_prompt


# 判断 LLM 调用抛出的异常是否属于 Day10 第一版可重试错误。
def is_retryable_external_error(exc: Exception) -> bool:
    return isinstance(exc, (TimeoutError, ConnectionError, OSError))



# 组装治理后的上下文并生成最终 RAG 回答。
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

    # 用 breaker + retry 保护真正的 LLM 调用，避免短暂故障直接打穿链路。
    async def invoke_llm() -> str:
        before_call(
            name="llm",
            recovery_timeout_seconds=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS,
        )
        try:
            answer_text = await chain.ainvoke(
                {
                    "context": context_packet["context_text"],
                    "question": question,
                }
            )
            record_success(name="llm")
            return answer_text
        except Exception:
            record_failure(
                name="llm",
                failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                recovery_timeout_seconds=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS,
            )
            raise

    answer = await retry_async(
        invoke_llm,
        is_retryable=is_retryable_external_error,
        max_attempts=settings.EXTERNAL_RETRY_MAX_ATTEMPTS,
        base_delay_seconds=settings.EXTERNAL_RETRY_BASE_DELAY_SECONDS,
        max_delay_seconds=settings.EXTERNAL_RETRY_MAX_DELAY_SECONDS,
    )

    return {
        "answer": answer,
        "sources": context_packet["sources"],
    }












