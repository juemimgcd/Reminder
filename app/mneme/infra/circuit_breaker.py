from time import time

from app.mneme.conf.logging import log_event
from app.mneme.utils.exceptions import BusinessException

# {
#     "milvus": {
#         "state": "open",
#         "failure_count": 3,
#         "reopen_at": 1776494669.43,
#     },
#     "llm": {
#         "state": "closed",
#         "failure_count": 0,
#         "reopen_at": 0.0,
#     },
# }
_BREAKER_STATE: dict[str, dict[str, float | int | str]] = {}


def before_call(*, name: str, recovery_timeout_seconds: int) -> None:
    curr = _BREAKER_STATE.get(name)
    if not curr:
        return

    state = str(curr["state"])
    reopen_at = float(curr.get("reopen_at", 0))

    if state == "open":
        if time() < reopen_at:
            log_event(
                "circuit_breaker",
                "warning",
                "breaker.blocked",
                name=name,
                state=state,
                reopen_at=reopen_at,
            )
            raise BusinessException(
                message=f"external dependency is temporarily unavailable: {name}",
                code=5031,
                status_code=503,
            )
        curr["state"] = "half_open"
        log_event("circuit_breaker", "info", "breaker.half_open", name=name)


def record_success(*, name: str) -> None:
    _BREAKER_STATE[name] = {
        "state": "closed",
        "failure_count": 0,
        "reopen_at": 0.0,
    }
    log_event("circuit_breaker", "info", "breaker.closed", name=name)


def record_failure(
        *,
        name: str,
        failure_threshold: int,
        recovery_timeout_seconds: int,
) -> None:
    state = _BREAKER_STATE.setdefault(
        name,
        {
            "state": "closed",
            "failure_count": 0,
            "reopen_at": 0.0,
        },
    )
    failure_count = int(state["failure_count"]) + 1
    state["failure_count"] = failure_count

    if failure_count >= failure_threshold:
        state["state"] = "open"
        state["reopen_at"] = time() + recovery_timeout_seconds
        log_event(
            "circuit_breaker",
            "warning",
            "breaker.opened",
            name=name,
            failure_count=failure_count,
            failure_threshold=failure_threshold,
            recovery_timeout_seconds=recovery_timeout_seconds,
        )
        return

    log_event(
        "circuit_breaker",
        "warning",
        "breaker.failure_recorded",
        name=name,
        failure_count=failure_count,
        failure_threshold=failure_threshold,
    )
