from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.mneme.memoria.server.api.dependencies import require_claimed_scope, require_service_scope
from app.mneme.memoria.server.api.errors import AgentAPIError
from app.mneme.memoria.server.repositories.runs import AnswerRunRepository
from app.mneme.memoria.server.runtime.contracts import AnswerRunData
from app.mneme.memoria.server.security.service_tokens import RUNS_READ_SCOPE

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
