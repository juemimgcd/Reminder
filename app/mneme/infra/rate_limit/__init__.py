from time import time

from app.mneme.conf.logging import log_event
from app.mneme.utils.exceptions import BusinessException

# {
#     "chat_query:user:1:kb:demo": {
#         "count": 3,
#         "window_end": 1776494000.12,
#     }
# }
_WINDOW_COUNTERS: dict[str, dict[str, float | int]] = {}


def enforce_fixed_window_rate_limit(
        *,
        bucket: str,
        key: str,
        limit: int,
        window_seconds: int,
) -> None:
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
            message=f"too many requests, please try again later: {bucket}",
            code=4290,
            status_code=429,
        )

    record["count"] = int(record["count"]) + 1






