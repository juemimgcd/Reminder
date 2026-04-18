import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from infra.circuit_breaker import _BREAKER_STATE, before_call, record_failure
from infra.rate_limit import enforce_fixed_window_rate_limit
from infra.retry import retry_async


# 记录 flaky_call 已经被调用了多少次，方便观察 retry 是否生效。
CALL_COUNT = {"flaky": 0}


# 模拟一个前两次超时、第三次成功的外部调用。
async def flaky_call():
    CALL_COUNT["flaky"] += 1
    if CALL_COUNT["flaky"] < 3:
        raise TimeoutError("temporary timeout")
    return "success"


# 指定当前调试脚本里哪些异常应被 retry_async 视为可重试。
def is_retryable(exc: Exception) -> bool:
    return isinstance(exc, TimeoutError)


# 依次演示 Day10 的限流、退避重试和熔断三种基础能力。
async def main():
    print("rate_limit_demo")
    for index in range(1, 5):
        try:
            enforce_fixed_window_rate_limit(
                bucket="chat_query",
                key="user:1:kb:demo",
                limit=3,
                window_seconds=60,
            )
            print(f"request_{index}=allowed")
        except Exception as exc:
            print(f"request_{index}=blocked:{exc}")

    print()
    print("retry_demo")
    result = await retry_async(
        flaky_call,
        is_retryable=is_retryable,
        max_attempts=3,
        base_delay_seconds=0.01,
        max_delay_seconds=0.02,
    )
    print(f"retry_result={result}")
    print(f"retry_call_count={CALL_COUNT['flaky']}")

    print()
    print("circuit_breaker_demo")
    for _ in range(3):
        record_failure(
            name="milvus",
            failure_threshold=3,
            recovery_timeout_seconds=30,
        )
    print(_BREAKER_STATE["milvus"])
    try:
        before_call(name="milvus", recovery_timeout_seconds=30)
    except Exception as exc:
        print(f"breaker_blocked={exc}")


if __name__ == "__main__":
    asyncio.run(main())
