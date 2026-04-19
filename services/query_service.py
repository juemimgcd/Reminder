from langchain_core.output_parsers import StrOutputParser

from clients.llm_client import get_llm
from conf.config import settings
from conf.logging import log_event
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
    log_event(
        "query_service",
        "info",
        "rag.answer.start",
        knowledge_base_id=knowledge_base_id,
        user_id=user_id,
        top_k=top_k,
        question_length=len(question),
    )
    context_packet = await build_query_context(
        query=question,
        top_k=top_k,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
    )
    log_event(
        "query_service",
        "info",
        "rag.context.ready",
        knowledge_base_id=knowledge_base_id,
        user_id=user_id,
        raw_count=context_packet["raw_count"],
        dedup_count=context_packet["dedup_count"],
        merged_count=context_packet["merged_count"],
        final_count=context_packet["final_count"],
    )

    if not context_packet["sources"]:
        log_event(
            "query_service",
            "warning",
            "rag.answer.empty_sources",
            knowledge_base_id=knowledge_base_id,
            user_id=user_id,
        )
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
            log_event(
                "query_service",
                "debug",
                "llm.invoke.start",
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
            )
            answer_text = await chain.ainvoke(
                {
                    "context": context_packet["context_text"],
                    "question": question,
                }
            )
            record_success(name="llm")
            log_event(
                "query_service",
                "info",
                "llm.invoke.completed",
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
                answer_length=len(answer_text),
            )
            return answer_text
        except Exception as exc:
            record_failure(
                name="llm",
                failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                recovery_timeout_seconds=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS,
            )
            app_logger.bind(module="query_service").exception(
                f"llm invoke failed knowledge_base_id={knowledge_base_id} user_id={user_id} "
                f"error_type={type(exc).__name__} error={exc}"
            )
            raise

    answer = await retry_async(
        invoke_llm,
        is_retryable=is_retryable_external_error,
        max_attempts=settings.EXTERNAL_RETRY_MAX_ATTEMPTS,
        base_delay_seconds=settings.EXTERNAL_RETRY_BASE_DELAY_SECONDS,
        max_delay_seconds=settings.EXTERNAL_RETRY_MAX_DELAY_SECONDS,
    )
    log_event(
        "query_service",
        "info",
        "rag.answer.completed",
        knowledge_base_id=knowledge_base_id,
        user_id=user_id,
        source_count=len(context_packet["sources"]),
    )

    return {
        "answer": answer,
        "sources": context_packet["sources"],
    }










