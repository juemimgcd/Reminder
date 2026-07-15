from typing import Annotated, Any

from fastapi import APIRouter, Depends

from services.memory_agent.api.dependencies import require_claimed_scope, require_service_scope
from services.memory_agent.api.errors import AgentAPIError
from services.memory_agent.contracts.answers import AnswerRequest, AnswerResponse
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
