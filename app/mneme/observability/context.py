import contextvars
import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
_run_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("run_id", default=None)
_event_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("event_id", default=None)
_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)

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


__all__ = ["correlation_fields", "observation_context", "safe_identifier"]
