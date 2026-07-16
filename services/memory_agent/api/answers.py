import asyncio
import json
from typing import Annotated, Any, AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from services.memory_agent.api.dependencies import require_claimed_scope, require_service_scope
from services.memory_agent.api.errors import AgentAPIError
from services.memory_agent.contracts.answers import AnswerRequest, AnswerResponse, AnswerStreamEvent
from services.memory_agent.providers.llm import ConfiguredModelGateway
from services.memory_agent.runtime.citations import EvidenceCitationValidator
from services.memory_agent.runtime.orchestrator import AnswerRunExecutionError, MemoryAgent, RuntimeDependencyError
from services.memory_agent.runtime.retriever import ScopedEvidenceRetriever
from services.memory_agent.security.service_tokens import ANSWERS_WRITE_SCOPE

router = APIRouter()


def get_memory_agent() -> MemoryAgent:
    return MemoryAgent(
        retriever=ScopedEvidenceRetriever(),
        generator=ConfiguredModelGateway(),
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

        async def emit(phase: str, status: str, run_id: str) -> None:
            await queue.put(
                AnswerStreamEvent(
                    type="phase",
                    run_id=run_id,
                    phase=phase,
                    status=status,
                )
            )

        async def execute() -> None:
            try:
                response = await agent.run(request, event_callback=emit)
                await queue.put(AnswerStreamEvent(type="final", run_id=response.run_id, response=response))
            except ValueError:
                await queue.put(AnswerStreamEvent(type="error", code="AGENT_VALIDATION_ERROR"))
            except (AnswerRunExecutionError, RuntimeDependencyError) as exc:
                await queue.put(
                    AnswerStreamEvent(
                        type="error",
                        run_id=getattr(exc, "run_id", None),
                        code=exc.error_code,
                    )
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                await queue.put(AnswerStreamEvent(type="error", code="AGENT_INTERNAL_ERROR"))
            finally:
                await queue.put(None)

        task = asyncio.create_task(execute())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                payload = json.dumps(event.model_dump(mode="json", exclude_none=True), separators=(",", ":"))
                yield f"event: {event.type}\ndata: {payload}\n\n"
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
