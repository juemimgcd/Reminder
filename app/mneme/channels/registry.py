from functools import lru_cache

from app.mneme.channels.adapters.feishu import FeishuAdapter
from app.mneme.channels.contracts import ChannelAdapter


@lru_cache(maxsize=4)
def get_channel_adapter(channel: str) -> ChannelAdapter:
    if channel == "feishu":
        return FeishuAdapter()
    raise ValueError(f"unsupported channel: {channel}")
