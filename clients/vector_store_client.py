import asyncio
import json
from typing import Any

from langchain_core.documents import Document as LCDocument
from langchain_milvus import Milvus

from conf.config import settings
from conf.logging import log_event
from clients.embedding_client import get_embeddings
from infra.circuit_breaker import before_call, record_success, record_failure
from infra.retry import retry_async


# 组装 Milvus 连接参数，兼容无 token 和带 token 两种配置。
def _build_connection_args() -> dict[str, str]:
    connection_args: dict[str, str] = {
        "uri": settings.MILVUS_URI,
        "db_name": settings.MILVUS_DB_NAME,
    }
    if settings.MILVUS_TOKEN:
        connection_args["token"] = settings.MILVUS_TOKEN
    return connection_args


# 从配置中解析 Milvus 检索参数 JSON。
def _build_search_params() -> dict[str, Any]:
    try:
        parsed = json.loads(settings.MILVUS_SEARCH_PARAMS)
    except json.JSONDecodeError:
        parsed = {}

    if isinstance(parsed, dict):
        return parsed
    return {}


# 基于当前配置生成 Milvus 索引参数。
def _build_index_params() -> dict[str, Any]:
    search_params = _build_search_params()
    metric_type = search_params.get("metric_type", settings.MILVUS_METRIC_TYPE)
    return {
        "index_type": settings.MILVUS_INDEX_TYPE,
        "metric_type": metric_type,
    }


# 创建当前项目使用的 Milvus vector store 客户端。
def get_vector_store() -> Milvus:
    log_event(
        "vector_store",
        "debug",
        "vector_store.client_built",
        backend=settings.VECTOR_BACKEND,
        collection=settings.MILVUS_COLLECTION_NAME,
    )
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


# 将一批 chunk 直接写入向量库。
async def add_documents_to_vector_store(chunk_docs: list[LCDocument]) -> None:
    if not chunk_docs:
        return

    vector_store = get_vector_store()
    ids = [str(chunk.metadata["chunk_id"]) for chunk in chunk_docs]
    log_event("vector_store", "info", "vector_store.add.start", chunk_count=len(chunk_docs))
    vector_store.add_documents(documents=chunk_docs, ids=ids)
    log_event("vector_store", "info", "vector_store.add.completed", chunk_count=len(chunk_docs))


# 按 chunk id 从向量库中删除指定文档块。
async def delete_documents_from_vector_store(*, ids: list[str] | None = None) -> None:
    if not ids:
        return

    vector_store = get_vector_store()
    log_event("vector_store", "info", "vector_store.delete.start", id_count=len(ids))
    vector_store.delete(ids=ids)
    log_event("vector_store", "info", "vector_store.delete.completed", id_count=len(ids))


# 删除当前项目使用的整个向量集合。
async def drop_vector_collection() -> None:
    vector_store = get_vector_store()
    log_event(
        "vector_store",
        "warning",
        "vector_store.collection_drop",
        collection=settings.MILVUS_COLLECTION_NAME,
    )
    vector_store.drop()


# 按 batch_size 将 chunk 列表切成多批，供批量写入使用。
def build_document_batches(
        chunk_docs: list[LCDocument],
        *,
        batch_size: int,
) -> list[list[LCDocument]]:
    # 你要做的事：
    # 1. 校验 batch_size > 0
    # 2. 按 batch_size 切片
    # 3. 返回二维列表
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")

    return [
        chunk_docs[index:index + batch_size]
        for index in range(0, len(chunk_docs), batch_size)
    ]


# 将 chunk 分批写入向量库，并返回批处理统计信息。
async def add_documents_to_vector_store_in_batches(
        *,
        chunk_docs: list[LCDocument],
        batch_size: int,
) -> dict:
    vector_store = get_vector_store()
    batches = build_document_batches(
        chunk_docs,
        batch_size=batch_size,
    )
    log_event(
        "vector_store",
        "info",
        "vector_store.batch_upsert.start",
        batch_count=len(batches),
        batch_size=batch_size,
        chunk_count=len(chunk_docs),
    )

    total_count = 0
    for batch_docs in batches:
        ids = [str(chunk.metadata["chunk_id"]) for chunk in batch_docs]
        await asyncio.to_thread(lambda: vector_store.add_documents(documents=batch_docs, ids=ids))
        total_count += len(batch_docs)
        log_event(
            "vector_store",
            "debug",
            "vector_store.batch_upsert.progress",
            current_batch_size=len(batch_docs),
            total_count=total_count,
        )

    log_event(
        "vector_store",
        "info",
        "vector_store.batch_upsert.completed",
        batch_count=len(batches),
        total_count=total_count,
        batch_size=batch_size,
    )
    return {
        "batch_count": len(batches),
        "total_count": total_count,
        "batch_size": batch_size,
    }


# 判断 Milvus 检索异常是否属于 Day10 第一版可重试错误。
def is_retryable_vector_error(exc: Exception) -> bool:
    return isinstance(exc, (TimeoutError, ConnectionError, OSError))


# 用 breaker + retry 包住 Milvus similarity_search_with_score 调用。
async def similarity_search_with_score_resilient(**search_kwargs):
    vector_store = get_vector_store()
    log_event(
        "vector_store",
        "debug",
        "vector_store.search.start",
        k=search_kwargs.get("k"),
        has_expr="expr" in search_kwargs,
    )

    # 真正执行一次检索调用，并在成功/失败时更新 breaker 状态。
    async def do_search():
        before_call(
            name="milvus",
            recovery_timeout_seconds=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS,
        )
        try:
            result = await asyncio.to_thread(
                lambda: vector_store.similarity_search_with_score(**search_kwargs)
            )
            record_success(name="milvus")
            log_event(
                "vector_store",
                "debug",
                "vector_store.search.completed",
                result_count=len(result),
            )
            return result
        except Exception as exc:
            record_failure(
                name="milvus",
                failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                recovery_timeout_seconds=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS,
            )
            app_logger.bind(module="vector_store").exception(
                f"vector similarity search failed error_type={type(exc).__name__} error={exc}"
            )
            raise

    return await retry_async(
        do_search,
        is_retryable=is_retryable_vector_error,
        max_attempts=settings.EXTERNAL_RETRY_MAX_ATTEMPTS,
        base_delay_seconds=settings.EXTERNAL_RETRY_BASE_DELAY_SECONDS,
        max_delay_seconds=settings.EXTERNAL_RETRY_MAX_DELAY_SECONDS,
    )

