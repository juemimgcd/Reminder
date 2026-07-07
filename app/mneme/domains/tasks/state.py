from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.logging import app_logger
from app.mneme.crud.task_record import get_task_record_by_id, update_task_record_status
from app.mneme.utils.exceptions import BusinessException


PENDING = "pending"
RUNNING = "running"
SUCCEEDED = "succeeded"
FAILED = "failed"
RETRYING = "retrying"
CANCELLED = "cancelled"

TERMINAL_TASK_STATUSES = {SUCCEEDED, FAILED, CANCELLED}
ACTIVE_TASK_STATUSES = {PENDING, RUNNING, RETRYING}

LEGACY_STATUS_ALIASES = {
    "queued": PENDING,
    "completed": SUCCEEDED,
    "canceled": CANCELLED,
}

PROGRESS_STAGE_STATUSES = {
    "parsing",
    "chunking",
    "memory_extracting",
    "embedding",
    "vector_upserting",
    "graph_projecting",
    "eval_running",
}

ALLOWED_TASK_TRANSITIONS = {
    PENDING: {RUNNING, FAILED, CANCELLED},
    RUNNING: {SUCCEEDED, FAILED, RETRYING, CANCELLED},
    RETRYING: {PENDING, RUNNING, FAILED, CANCELLED},
    FAILED: {RETRYING, PENDING},
    CANCELLED: {RETRYING, PENDING},
    SUCCEEDED: set(),
}


def normalize_task_status(status: str) -> str:
    if status in PROGRESS_STAGE_STATUSES:
        return RUNNING
    return LEGACY_STATUS_ALIASES.get(status, status)


def is_active_task_status(status: str) -> bool:
    return normalize_task_status(status) in ACTIVE_TASK_STATUSES


def resolve_task_transition(*, current_status: str, requested_status: str) -> tuple[str, str | None]:
    normalized_current = normalize_task_status(current_status)
    progress_stage = None

    if requested_status in PROGRESS_STAGE_STATUSES:
        progress_stage = requested_status
        normalized_requested = RUNNING
    else:
        normalized_requested = normalize_task_status(requested_status)

    if normalized_current == normalized_requested:
        return normalized_requested, progress_stage

    allowed_statuses = ALLOWED_TASK_TRANSITIONS.get(normalized_current, set())
    if normalized_requested not in allowed_statuses:
        raise BusinessException(
            message=f"illegal task status transition: {normalized_current} -> {normalized_requested}",
            code=4009,
            status_code=400,
        )

    return normalized_requested, progress_stage


async def transition_task_status(
        db: AsyncSession,
        *,
        task_id: str,
        to_status: str,
        result_summary: str | None = None,
        error_message: str | None = None,
):
    task_recd = await get_task_record_by_id(db, task_id=task_id)
    if not task_recd:
        app_logger.bind(module="task_state").warning(
            f"task status transition target missing task_id={task_id} to_status={to_status}"
        )
        return None

    previous_status = normalize_task_status(task_recd.status)
    try:
        next_status, progress_stage = resolve_task_transition(
            current_status=task_recd.status,
            requested_status=to_status,
        )
    except BusinessException:
        app_logger.bind(module="task_state").warning(
            f"task status illegal transition task_id={task_id} "
            f"from_status={task_recd.status} to_status={to_status}"
        )
        raise

    if previous_status == next_status and progress_stage is None:
        app_logger.bind(module="task_state").info(
            f"task status unchanged task_id={task_id} status={next_status}"
        )
        return task_recd

    app_logger.bind(module="task_state").info(
        f"task status transition task_id={task_id} from_status={task_recd.status} "
        f"to_status={next_status} progress_stage={progress_stage}"
    )
    return await update_task_record_status(
        db,
        task_id=task_id,
        status=next_status,
        progress_stage=progress_stage,
        clear_progress_stage=progress_stage is None and next_status in {PENDING, RETRYING, CANCELLED},
        increment_attempt=next_status == RUNNING and previous_status in {PENDING, RETRYING},
        result_summary=result_summary,
        error_message=error_message,
        clear_error=next_status in {PENDING, RUNNING, SUCCEEDED, RETRYING},
    )
