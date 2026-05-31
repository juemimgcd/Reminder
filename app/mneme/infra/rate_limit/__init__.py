from time import time

from app.mneme.conf.logging import log_event
from app.mneme.utils.exceptions import BusinessException


# 杩涚▼鍐呭浐瀹氱獥鍙ｈ鏁板櫒锛宬ey 褰㈠ "chat_query:user:1:kb:demo"銆?
# 缁撴瀯绀轰緥锛?
# {
#     "chat_query:user:1:kb:demo": {
#         "count": 3,
#         "window_end": 1776494000.12,
#     }
# }
_WINDOW_COUNTERS: dict[str, dict[str, float | int]] = {}


# 瀵规寚瀹?bucket + key 鎵ц涓€娆¤繘绋嬪唴鍥哄畾绐楀彛闄愭祦妫€鏌ャ€?
def enforce_fixed_window_rate_limit(
        *,
        bucket: str,
        key: str,
        limit: int,
        window_seconds: int,
) -> None:
    # 浣犺鍋氱殑浜嬶細
    # 1. 鐢熸垚 bucket + key 瀵瑰簲鐨勮鏁伴敭
    # 2. 鎵惧埌褰撳墠绐楀彛璧风偣
    # 3. 濡傛灉绐楀彛宸茶繃鏈燂紝閲嶇疆璁℃暟
    # 4. 瓒呰繃 limit 鏃舵姏 BusinessException
    # 5. 娌¤秴杩囧垯璁℃暟 +1
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






