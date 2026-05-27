import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.mneme.infra.circuit_breaker import _BREAKER_STATE, before_call, record_failure
from app.mneme.infra.rate_limit import enforce_fixed_window_rate_limit
from app.mneme.infra.retry import retry_async


# 璁板綍 flaky_call 宸茬粡琚皟鐢ㄤ簡澶氬皯娆★紝鏂逛究瑙傚療 retry 鏄惁鐢熸晥銆?
CALL_COUNT = {"flaky": 0}


# 妯℃嫙涓€涓墠涓ゆ瓒呮椂銆佺涓夋鎴愬姛鐨勫閮ㄨ皟鐢ㄣ€?
async def flaky_call():
    CALL_COUNT["flaky"] += 1
    if CALL_COUNT["flaky"] < 3:
        raise TimeoutError("temporary timeout")
    return "success"


# 鎸囧畾褰撳墠璋冭瘯鑴氭湰閲屽摢浜涘紓甯稿簲琚?retry_async 瑙嗕负鍙噸璇曘€?
def is_retryable(exc: Exception) -> bool:
    return isinstance(exc, TimeoutError)


# 渚濇婕旂ず Day10 鐨勯檺娴併€侀€€閬块噸璇曞拰鐔旀柇涓夌鍩虹鑳藉姏銆?
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
