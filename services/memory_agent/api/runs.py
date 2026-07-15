from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from services.memory_agent.api.dependencies import require_claimed_scope, require_service_scope
from services.memory_agent.api.errors import AgentAPIError
from services.memory_agent.repositories.runs import AnswerRunRepository
from services.memory_agent.runtime.contracts import AnswerRunData
from services.memory_agent.security.service_tokens import RUNS_READ_SCOPE

router = APIRouter()


@router.get("/runs/{run_id}", response_model=AnswerRunData)
async def get_run(
    run_id: str,
    claims: Annotated[dict[str, Any], Depends(require_service_scope(RUNS_READ_SCOPE))],
    owner_id: int = Query(gt=0),
    knowledge_base_id: str | None = Query(default=None, max_length=128),
) -> AnswerRunData:
    require_claimed_scope(claims, owner_id=owner_id, knowledge_base_id=knowledge_base_id)
    try:
        run = await AnswerRunRepository().get(run_id)
    except LookupError:
        raise AgentAPIError(status_code=404, code="AGENT_RUN_NOT_FOUND") from None
    if run.owner_id != owner_id or run.knowledge_base_id != knowledge_base_id:
        raise AgentAPIError(status_code=404, code="AGENT_RUN_NOT_FOUND")
    return run
