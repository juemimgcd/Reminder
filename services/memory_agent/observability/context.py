import contextvars
import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
_run_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("run_id", default=None)
_event_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("event_id", default=None)


@contextmanager
def observation_context(
    *, request_id: str | None = None, run_id: str | None = None, event_id: str | None = None
) -> Iterator[None]:
    tokens: list[tuple[contextvars.ContextVar[str | None], contextvars.Token[str | None]]] = []
    for variable, value in ((_request_id, request_id), (_run_id, run_id), (_event_id, event_id)):
        if value is not None:
            tokens.append((variable, variable.set(value)))
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
        )
        if value is not None
    }


class SafeJsonFormatter(logging.Formatter):
    """Emit identifiers and operator-safe metadata, never request content."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "service": "memory_agent",
            "logger": record.name,
            "message": record.getMessage(),
            **correlation_fields(),
        }
        if record.exc_info:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
