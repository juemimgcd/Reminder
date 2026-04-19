from time import time

from conf.logging import log_event
from utils.exceptions import BusinessException

# 进程内熔断器状态表，按依赖名保存当前 breaker 状态。
# 结构示例：
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


# 在真正调用外部依赖前检查 breaker 是否允许放行。
def before_call(*, name: str, recovery_timeout_seconds: int) -> None:
    # 你要做的事：
    # 1. 读取 breaker 状态
    # 2. 如果是 open 且还没到恢复时间，直接拒绝
    # 3. 如果已到恢复时间，切成 half_open
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
                message=f"外部依赖暂时不可用: {name}",
                code=5031,
                status_code=503,
            )
        curr["state"] = "half_open"
        log_event("circuit_breaker", "info", "breaker.half_open", name=name)


# 在外部依赖调用成功后重置对应 breaker 状态。
def record_success(*, name: str) -> None:
    # 你要做的事：
    # 1. 成功后清零失败计数
    # 2. 状态切回 closed
    _BREAKER_STATE[name] = {
        "state": "closed",
        "failure_count": 0,
        "reopen_at": 0.0,
    }
    log_event("circuit_breaker", "info", "breaker.closed", name=name)


# 在外部依赖调用失败后累计失败次数，并在达到阈值时打开 breaker。
def record_failure(
        *,
        name: str,
        failure_threshold: int,
        recovery_timeout_seconds: int,
) -> None:
    # 你要做的事：
    # 1. 失败计数 +1
    # 2. 达到阈值时切成 open
    # 3. 记录 reopen 时间
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
