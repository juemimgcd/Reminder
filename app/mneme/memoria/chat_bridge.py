"""Translate Mneme chat requests to the Memoria service contract."""

import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.memoria.clients.memory_agent import MemoryAgentClient, MemoryAgentUnavailable
from app.mneme.memoria.configuration.repository import get_ai_model_config, get_default_ai_model_config
from app.mneme.memoria.configuration.service import decrypt_api_key
from app.mneme.memoria.contracts import AnswerMode
from app.mneme.memoria.router import route_answer_mode
from app.mneme.memoria.schemas.memory_agent import (
    ConversationContextData,
    MemoryAgentAnswerRequest,
    MemoryAgentAnswerResponse,
    MemoryAgentStreamEvent,
    ModelInvocationConfig,
)
from app.mneme.utils.exceptions import BusinessException


async def resolve_model_config(db: AsyncSession, *, user_id: int, config_id: str | None):
    if config_id is not None:
        config = await get_ai_model_config(db, config_id=config_id, user_id=user_id)
        if config is None or not config.enabled:
            raise BusinessException(message="AI model config not found", code=4061, status_code=404)
        return config
    return await get_default_ai_model_config(db, user_id=user_id)


def _model_invocation_config(model_config) -> ModelInvocationConfig | None:
    if model_config is None:
        return None
    return ModelInvocationConfig(
        provider=model_config.provider,
        base_url=model_config.base_url,
        model_name=model_config.model_name,
        api_key=decrypt_api_key(model_config.api_key_ciphertext),
        temperature=model_config.temperature,
        context_window=model_config.context_window,
    )


async def answer_via_memory_agent(
    *,
    owner_id: int,
    question: str,
    answer_mode: AnswerMode,
    top_k: int,
    knowledge_base_id: str | None,
    session_id: str | None,
    message_id: str,
    model_config=None,
    idempotency_key: str | None = None,
    trace_id: str | None = None,
    event_callback: Callable[[MemoryAgentStreamEvent], Awaitable[None]] | None = None,
    conversation: ConversationContextData | None = None,
) -> MemoryAgentAnswerResponse:
    if answer_mode != "general_chat" and knowledge_base_id is None:
        raise BusinessException(message="knowledge base is required for this answer mode", code=4053)
    request = MemoryAgentAnswerRequest(
        request_id=f"answer_{message_id}_{idempotency_key or uuid.uuid4().hex}",
        trace_id=trace_id or f"trace_{message_id}",
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        session_id=session_id,
        message_id=message_id,
        question=question,
        answer_mode=answer_mode,
        top_k=top_k,
        allow_model_fallback=model_config is None,
        conversation=conversation or ConversationContextData(),
        model=_model_invocation_config(model_config),
    )
    async with MemoryAgentClient() as client:
        if event_callback is not None:
            final_response: MemoryAgentAnswerResponse | None = None
            try:
                async for event in client.stream_answer(request):
                    await event_callback(event)
                    if event.type == "final" and event.response is not None:
                        final_response = event.response
            except MemoryAgentUnavailable:
                return await client.create_answer(request)
            if final_response is None:
                raise MemoryAgentUnavailable("memory agent stream ended without a final response")
            return final_response
        return await client.create_answer(request)


def memory_agent_answer_to_chat_result(response: MemoryAgentAnswerResponse) -> dict:
    confidence = "high" if response.confidence >= 0.75 else "medium" if response.confidence >= 0.4 else "low"
    route = route_answer_mode(response.mode).model_dump()
    route["confidence"] = confidence
    route["reason"] = "user-selected answer mode"
    citations = []
    sources = []
    for item in response.citations:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        source_type = item.get("source_type") if isinstance(item.get("source_type"), str) else None
        source_id = item.get("source_id") if isinstance(item.get("source_id"), str) else None
        evidence_id = item.get("evidence_id") if isinstance(item.get("evidence_id"), str) else None
        quote = item.get("quote") if isinstance(item.get("quote"), str) else ""
        document_id = metadata.get("document_id") if isinstance(metadata.get("document_id"), str) else None
        chunk_id = source_id if source_type == "document" else None
        source_time = metadata.get("source_time") or metadata.get("valid_from") or metadata.get("created_at")
        citations.append(
            {
                "source_id": source_id,
                "document_id": document_id,
                "chunk_id": chunk_id,
                "page_no": metadata.get("page_no"),
                "quote": quote,
                "reason": "memory agent evidence",
                "source_type": source_type,
                "evidence_id": evidence_id,
                "source_time": source_time,
                "validation_status": "valid",
            }
        )
        sources.append(
            {
                "source_id": source_id,
                "knowledge_base_id": None,
                "document_id": document_id,
                "chunk_id": chunk_id,
                "page_no": metadata.get("page_no"),
                "text": quote,
                "source_type": source_type,
                "evidence_id": evidence_id,
                "source_time": source_time,
            }
        )
    return {
        "answer": response.answer,
        "sources": sources,
        "citations": citations,
        "confidence": confidence,
        "uncertainty": response.uncertainty,
        "insufficient_evidence": response.insufficient_evidence,
        "confidence_numeric": response.confidence,
        "route": route,
        "debug": None,
    }
