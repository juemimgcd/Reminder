import contextvars
import json
import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Final

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
_run_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("run_id", default=None)
_event_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("event_id", default=None)
_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)

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
    {"mode", "phase", "status", "error_code", "duration_ms", "count", "method", "http_status"}
)
SAFE_IDENTIFIER: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")


def safe_identifier(value: str | None) -> str | None:
    if value is None or SAFE_IDENTIFIER.fullmatch(value) is None:
        return None
    return value


@contextmanager
def observation_context(
    *,
    request_id: str | None = None,
    run_id: str | None = None,
    event_id: str | None = None,
    trace_id: str | None = None,
) -> Iterator[None]:
    tokens: list[tuple[contextvars.ContextVar[str | None], contextvars.Token[str | None]]] = []
    for variable, value in (
        (_request_id, request_id),
        (_run_id, run_id),
        (_event_id, event_id),
        (_trace_id, trace_id),
    ):
        safe_value = safe_identifier(value)
        if safe_value is not None:
            tokens.append((variable, variable.set(safe_value)))
    try:
        yield
    finally:
        for variable, token in reversed(tokens):
            variable.reset(token)


def correlation_fields() -> dict[str, str]:
    return {
        key: value
        for key, value in (
            ("request_id", _request_id.get()),
            ("run_id", _run_id.get()),
            ("event_id", _event_id.get()),
            ("trace_id", _trace_id.get()),
        )
        if value is not None
    }


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
