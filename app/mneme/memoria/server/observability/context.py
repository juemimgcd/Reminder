import json
import logging
from typing import Any, Final

from app.mneme.observability.context import correlation_fields, observation_context, safe_identifier

SAFE_EVENTS: Final = frozenset(
    {
        "answer_phase",
        "event_enqueue_failed",
        "request_completed",
        "request_failed",
        "runtime_log",
    }
)
SAFE_FIELDS: Final = frozenset(
    {"mode", "phase", "status", "error_code", "duration_ms", "count", "method", "route", "http_status"}
)


def safe_log(logger: logging.Logger, level: int, event: str, **fields: str | int | float | bool) -> None:
    safe_event = event if event in SAFE_EVENTS else "runtime_log"
    safe_fields = {key: value for key, value in fields.items() if key in SAFE_FIELDS}
    logger.log(level, safe_event, extra={"safe_event": safe_event, "safe_fields": safe_fields})


class SafeJsonFormatter(logging.Formatter):
    """Ignore arbitrary messages, args and exceptions; render only explicit safe fields."""

    def format(self, record: logging.LogRecord) -> str:
        event = getattr(record, "safe_event", "runtime_log")
        if event not in SAFE_EVENTS:
            event = "runtime_log"
        supplied = getattr(record, "safe_fields", {})
        safe_fields: dict[str, Any] = {}
        if isinstance(supplied, dict):
            safe_fields = {
                key: value
                for key, value in supplied.items()
                if key in SAFE_FIELDS and isinstance(value, (str, int, float, bool))
            }
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "service": "memory_agent",
            "event": event,
            **correlation_fields(),
            **safe_fields,
        }
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


__all__ = [
    "SafeJsonFormatter",
    "correlation_fields",
    "observation_context",
    "safe_identifier",
    "safe_log",
]
