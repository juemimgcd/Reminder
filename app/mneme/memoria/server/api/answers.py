import asyncio
import json
from typing import Annotated, Any, AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.mneme.memoria.server.api.dependencies import require_claimed_scope, require_service_scope
from app.mneme.memoria.server.api.errors import AgentAPIError
from app.mneme.memoria.server.contracts.answers import AnswerRequest, AnswerResponse, AnswerStreamEvent
from app.mneme.memoria.server.providers.llm import ConfiguredModelGateway
from app.mneme.memoria.server.runtime.citations import EvidenceCitationValidator
from app.mneme.memoria.server.runtime.orchestrator import (
    AnswerRunExecutionError,
    MemoryAgent,
    RuntimeDependencyError,
)
from app.mneme.memoria.server.runtime.retriever import ScopedEvidenceRetriever
from app.mneme.memoria.server.runtime.streaming import answer_chunks, phase_event_name
from app.mneme.memoria.server.runtime.tools import ScopedToolExecutor
from app.mneme.memoria.server.security.service_tokens import ANSWERS_WRITE_SCOPE

router = APIRouter()


def get_memory_agent() -> MemoryAgent:
    retriever = ScopedEvidenceRetriever()
    return MemoryAgent(
        retriever=retriever,
        generator=ConfiguredModelGateway(tool_executor=ScopedToolExecutor(retriever)),
        citation_validator=EvidenceCitationValidator(),
    )


def _runtime_error(code: str) -> AgentAPIError:
    if code.endswith("_TIMEOUT"):
        return AgentAPIError(status_code=504, code=code)
    if code == "AGENT_CAPACITY_EXCEEDED":
        return AgentAPIError(status_code=429, code=code)
    if code == "AGENT_REQUEST_IN_PROGRESS":
        return AgentAPIError(status_code=503, code=code)
    if code == "AGENT_MODEL_AUTH_FAILED":
        return AgentAPIError(status_code=422, code=code)
    if "UNAVAILABLE" in code:
        return AgentAPIError(status_code=503, code="AGENT_UNAVAILABLE")
    return AgentAPIError(status_code=500, code="AGENT_INTERNAL_ERROR")


@router.post("/answers", response_model=AnswerResponse)
async def create_answer(
    request: AnswerRequest,
    claims: Annotated[dict[str, Any], Depends(require_service_scope(ANSWERS_WRITE_SCOPE))],
    agent: Annotated[MemoryAgent, Depends(get_memory_agent)],
) -> AnswerResponse:
    require_claimed_scope(
        claims,
        owner_id=request.owner_id,
        knowledge_base_id=request.knowledge_base_id,
    )
    try:
        return await agent.run(request)
    except ValueError:
        raise AgentAPIError(status_code=422, code="AGENT_VALIDATION_ERROR") from None
    except AnswerRunExecutionError as exc:
        raise _runtime_error(exc.error_code) from None
    except RuntimeDependencyError as exc:
        raise _runtime_error(exc.error_code) from None
    except Exception:
        raise AgentAPIError(status_code=500, code="AGENT_INTERNAL_ERROR") from None


@router.post("/answers/stream", response_class=StreamingResponse)
async def stream_answer(
    request: AnswerRequest,
    claims: Annotated[dict[str, Any], Depends(require_service_scope(ANSWERS_WRITE_SCOPE))],
    agent: Annotated[MemoryAgent, Depends(get_memory_agent)],
) -> StreamingResponse:
    require_claimed_scope(
        claims,
        owner_id=request.owner_id,
        knowledge_base_id=request.knowledge_base_id,
    )

    async def event_source() -> AsyncIterator[str]:
        queue: asyncio.Queue[AnswerStreamEvent | None] = asyncio.Queue()
        next_sequence = 0

        def build_event(**values: Any) -> AnswerStreamEvent:
            nonlocal next_sequence
            next_sequence += 1
            return AnswerStreamEvent(sequence=next_sequence, **values)

        async def emit(
            phase: str,
            status: str,
            run_id: str,
            public_payload: dict[str, Any],
        ) -> None:
            if phase.startswith("multi_agent."):
                event_name = public_payload.get("event_name")
                if isinstance(event_name, str):
                    await queue.put(
                        build_event(
                            type="phase",
                            name=event_name,
                            run_id=run_id,
                            phase=phase,
                            status=status,
                            public_payload={
                                key: value
                                for key, value in public_payload.items()
                                if key != "event_name" and value is not None
                            },
                        )
                    )
                return
            if phase == "retrieve" and status == "completed":
                source_counts = public_payload.get("source_counts")
                if isinstance(source_counts, dict):
                    for source_type, result_count in sorted(source_counts.items()):
                        if not isinstance(source_type, str) or not isinstance(result_count, int):
                            continue
                        await queue.put(
                            build_event(
                                type="phase",
                                name="retrieval.source_completed",
                                run_id=run_id,
                                phase=phase,
                                status=status,
                                public_payload={
                                    "source_type": source_type,
                                    "result_count": result_count,
                                },
                            )
                        )
                await queue.put(
                    build_event(
                        type="phase",
                        name="evidence.selected",
                        run_id=run_id,
                        phase=phase,
                        status=status,
                        public_payload=public_payload,
                    )
                )
                return
            name = phase_event_name(phase, status)
            if name is None:
                return
            await queue.put(
                build_event(
                    type="phase",
                    name=name,
                    run_id=run_id,
                    phase=phase,
                    status=status,
                    public_payload=public_payload,
                )
            )

        async def execute() -> None:
            try:
                response = await agent.run(request, event_callback=emit)
                for content in answer_chunks(response.answer):
                    await queue.put(
                        build_event(
                            type="delta",
                            name="answer.delta",
                            run_id=response.run_id,
                            phase="answer",
                            status="streaming",
                            content=content,
                        )
                    )
                    # Give the transport a scheduling point so validated chunks are
                    # flushed as observable deltas instead of one coalesced frame.
                    await asyncio.sleep(0.02)
                await queue.put(
                    build_event(
                        type="final",
                        name="answer.completed",
                        run_id=response.run_id,
                        phase="answer",
                        status="completed",
                        response=response,
                        public_payload={
                            "citation_count": len(response.citations),
                            "insufficient_evidence": response.insufficient_evidence,
                        },
                    )
                )
            except ValueError:
                await queue.put(
                    build_event(
                        type="error",
                        name="run.failed",
                        code="AGENT_VALIDATION_ERROR",
                    )
                )
            except (AnswerRunExecutionError, RuntimeDependencyError) as exc:
                await queue.put(
                    build_event(
                        type="error",
                        name="run.failed",
                        run_id=getattr(exc, "run_id", None),
                        code=exc.error_code,
                    )
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                await queue.put(
                    build_event(
                        type="error",
                        name="run.failed",
                        code="AGENT_INTERNAL_ERROR",
                    )
                )
            finally:
                await queue.put(None)

        task = asyncio.create_task(execute())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                payload = json.dumps(event.model_dump(mode="json", exclude_none=True), separators=(",", ":"))
                yield f"id: {event.sequence}\nevent: {event.name}\ndata: {payload}\n\n"
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
