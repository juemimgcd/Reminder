import asyncio
import json
from typing import Any

from langchain_core.documents import Document as LCDocument
from langchain_milvus import Milvus

from app.mneme.conf.config import settings
from app.mneme.conf.logging import log_event, app_logger
from app.mneme.clients.embedding_client import get_embeddings
from app.mneme.infra.circuit_breaker import before_call, record_success, record_failure
from app.mneme.infra.object_cache import get_cached_object, set_cached_object
from app.mneme.infra.retry import retry_async


def _sanitize_metadata_for_milvus(metadata: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        sanitized[key] = value
    return sanitized


def _sanitize_documents_for_milvus(chunk_docs: list[LCDocument]) -> list[LCDocument]:
    sanitized_docs: list[LCDocument] = []
    for chunk in chunk_docs:
        sanitized_docs.append(
            LCDocument(
                page_content=chunk.page_content,
                metadata=_sanitize_metadata_for_milvus(chunk.metadata),
            )
        )
    return sanitized_docs


# 缁勮 Milvus 杩炴帴鍙傛暟锛屽吋瀹规棤 token 鍜屽甫 token 涓ょ閰嶇疆銆?
def _build_connection_args() -> dict[str, str]:
    connection_args: dict[str, str] = {
        "uri": settings.MILVUS_URI,
        "db_name": settings.MILVUS_DB_NAME,
    }
    if settings.MILVUS_TOKEN:
        connection_args["token"] = settings.MILVUS_TOKEN
    return connection_args


# 浠庨厤缃腑瑙ｆ瀽 Milvus 妫€绱㈠弬鏁?JSON銆?
def _build_search_params() -> dict[str, Any]:
    try:
        parsed = json.loads(settings.MILVUS_SEARCH_PARAMS)
    except json.JSONDecodeError:
        parsed = {}

    if isinstance(parsed, dict):
        return parsed
    return {}


# 鍩轰簬褰撳墠閰嶇疆鐢熸垚 Milvus 绱㈠紩鍙傛暟銆?
def _build_index_params() -> dict[str, Any]:
    search_params = _build_search_params()
    metric_type = search_params.get("metric_type", settings.MILVUS_METRIC_TYPE)
    return {
        "index_type": settings.MILVUS_INDEX_TYPE,
        "metric_type": metric_type,
    }


# 鍒涘缓褰撳墠椤圭洰浣跨敤鐨?Milvus vector store 瀹㈡埛绔€?
def get_vector_store() -> Milvus:
    cached = get_cached_object("vector_store_client")
    if isinstance(cached, Milvus):
        return cached

    log_event(
        "vector_store",
        "debug",
        "vector_store.client_built",
        backend=settings.VECTOR_BACKEND,
        collection=settings.MILVUS_COLLECTION_NAME,
    )
    vector_store = Milvus(
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
    return set_cached_object("vector_store_client", vector_store)


# 灏嗕竴鎵?chunk 鐩存帴鍐欏叆鍚戦噺搴撱€?
async def add_documents_to_vector_store(chunk_docs: list[LCDocument]) -> None:
    if not chunk_docs:
        return

    vector_store = get_vector_store()
    sanitized_docs = _sanitize_documents_for_milvus(chunk_docs)
    ids = [str(chunk.metadata["chunk_id"]) for chunk in sanitized_docs]
    log_event("vector_store", "info", "vector_store.add.start", chunk_count=len(chunk_docs))
    vector_store.add_documents(documents=sanitized_docs, ids=ids)
    log_event("vector_store", "info", "vector_store.add.completed", chunk_count=len(chunk_docs))


# 鎸?chunk id 浠庡悜閲忓簱涓垹闄ゆ寚瀹氭枃妗ｅ潡銆?
async def delete_documents_from_vector_store(*, ids: list[str] | None = None) -> None:
    if not ids:
        return

    vector_store = get_vector_store()
    log_event("vector_store", "info", "vector_store.delete.start", id_count=len(ids))
    vector_store.delete(ids=ids)
    log_event("vector_store", "info", "vector_store.delete.completed", id_count=len(ids))


# 鍒犻櫎褰撳墠椤圭洰浣跨敤鐨勬暣涓悜閲忛泦鍚堛€?
async def drop_vector_collection() -> None:
    vector_store = get_vector_store()
    log_event(
        "vector_store",
        "warning",
        "vector_store.collection_drop",
        collection=settings.MILVUS_COLLECTION_NAME,
    )
    vector_store.drop()


# 鎸?batch_size 灏?chunk 鍒楄〃鍒囨垚澶氭壒锛屼緵鎵归噺鍐欏叆浣跨敤銆?
def build_document_batches(
        chunk_docs: list[LCDocument],
        *,
        batch_size: int,
) -> list[list[LCDocument]]:
    # 浣犺鍋氱殑浜嬶細
    # 1. 鏍￠獙 batch_size > 0
    # 2. 鎸?batch_size 鍒囩墖
    # 3. 杩斿洖浜岀淮鍒楄〃
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")

    return [
        chunk_docs[index:index + batch_size]
        for index in range(0, len(chunk_docs), batch_size)
    ]


# 灏?chunk 鍒嗘壒鍐欏叆鍚戦噺搴擄紝骞惰繑鍥炴壒澶勭悊缁熻淇℃伅銆?
async def add_documents_to_vector_store_in_batches(
        *,
        chunk_docs: list[LCDocument],
        batch_size: int,
) -> dict:
    vector_store = get_vector_store()
    sanitized_docs = _sanitize_documents_for_milvus(chunk_docs)
    batches = build_document_batches(
        sanitized_docs,
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


# 鍒ゆ柇 Milvus 妫€绱㈠紓甯告槸鍚﹀睘浜?Day10 绗竴鐗堝彲閲嶈瘯閿欒銆?
def is_retryable_vector_error(exc: Exception) -> bool:
    return isinstance(exc, (TimeoutError, ConnectionError, OSError))


# 鐢?breaker + retry 鍖呬綇 Milvus similarity_search_with_score 璋冪敤銆?
async def similarity_search_with_score_resilient(**search_kwargs):
    vector_store = get_vector_store()
    log_event(
        "vector_store",
        "debug",
        "vector_store.search.start",
        k=search_kwargs.get("k"),
        has_expr="expr" in search_kwargs,
    )

    # 鐪熸鎵ц涓€娆℃绱㈣皟鐢紝骞跺湪鎴愬姛/澶辫触鏃舵洿鏂?breaker 鐘舵€併€?
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

