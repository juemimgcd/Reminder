from time import time

from conf.logging import log_event
from utils.exceptions import BusinessException


# 进程内固定窗口计数器，key 形如 "chat_query:user:1:kb:demo"。
# 结构示例：
# {
#     "chat_query:user:1:kb:demo": {
#         "count": 3,
#         "window_end": 1776494000.12,
#     }
# }
_WINDOW_COUNTERS: dict[str, dict[str, float | int]] = {}


# 对指定 bucket + key 执行一次进程内固定窗口限流检查。
def enforce_fixed_window_rate_limit(
        *,
        bucket: str,
        key: str,
        limit: int,
        window_seconds: int,
) -> None:
    # 你要做的事：
    # 1. 生成 bucket + key 对应的计数键
    # 2. 找到当前窗口起点
    # 3. 如果窗口已过期，重置计数
    # 4. 超过 limit 时抛 BusinessException
    # 5. 没超过则计数 +1
    if limit <= 0:
        return

    counter_key = f"{bucket}:{key}"
    now = time()
    record = _WINDOW_COUNTERS.get(counter_key)

    if not record or (now >= float(record["window_end"])):
        record = {
            "count":0,
            "window_end":now+window_seconds
        }
        _WINDOW_COUNTERS[counter_key] = record

    if int(record["count"]) >= limit:
        log_event(
            "rate_limit",
            "warning",
            "rate_limit.blocked",
            bucket=bucket,
            key=key,
            count=int(record["count"]),
            limit=limit,
            window_seconds=window_seconds,
        )
        raise BusinessException(
            message=f"请求过于频繁，请稍后再试: {bucket}",
            code=4290,
            status_code=429,
        )

    record["count"] = int(record["count"]) + 1






