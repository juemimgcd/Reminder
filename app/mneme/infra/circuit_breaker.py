from time import time

from app.mneme.conf.logging import log_event
from app.mneme.utils.exceptions import BusinessException

# 杩涚▼鍐呯啍鏂櫒鐘舵€佽〃锛屾寜渚濊禆鍚嶄繚瀛樺綋鍓?breaker 鐘舵€併€?
# 缁撴瀯绀轰緥锛?
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


# 鍦ㄧ湡姝ｈ皟鐢ㄥ閮ㄤ緷璧栧墠妫€鏌?breaker 鏄惁鍏佽鏀捐銆?
def before_call(*, name: str, recovery_timeout_seconds: int) -> None:
    # 浣犺鍋氱殑浜嬶細
    # 1. 璇诲彇 breaker 鐘舵€?
    # 2. 濡傛灉鏄?open 涓旇繕娌″埌鎭㈠鏃堕棿锛岀洿鎺ユ嫆缁?
    # 3. 濡傛灉宸插埌鎭㈠鏃堕棿锛屽垏鎴?half_open
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


# 鍦ㄥ閮ㄤ緷璧栬皟鐢ㄦ垚鍔熷悗閲嶇疆瀵瑰簲 breaker 鐘舵€併€?
def record_success(*, name: str) -> None:
    # 浣犺鍋氱殑浜嬶細
    # 1. 鎴愬姛鍚庢竻闆跺け璐ヨ鏁?
    # 2. 鐘舵€佸垏鍥?closed
    _BREAKER_STATE[name] = {
        "state": "closed",
        "failure_count": 0,
        "reopen_at": 0.0,
    }
    log_event("circuit_breaker", "info", "breaker.closed", name=name)


# 鍦ㄥ閮ㄤ緷璧栬皟鐢ㄥけ璐ュ悗绱澶辫触娆℃暟锛屽苟鍦ㄨ揪鍒伴槇鍊兼椂鎵撳紑 breaker銆?
def record_failure(
        *,
        name: str,
        failure_threshold: int,
        recovery_timeout_seconds: int,
) -> None:
    # 浣犺鍋氱殑浜嬶細
    # 1. 澶辫触璁℃暟 +1
    # 2. 杈惧埌闃堝€兼椂鍒囨垚 open
    # 3. 璁板綍 reopen 鏃堕棿
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
