import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.mneme.conf.logging import log_event


T = TypeVar("T")


async def retry_async(
        func: Callable[[], Awaitable[T]],
        *,
        is_retryable: Callable[[Exception], bool],
        max_attempts: int,
        base_delay_seconds: float,
        max_delay_seconds: float,
) -> T:
    attempt = 0

    while True:
        attempt += 1
        try:
            return await func()
        except Exception as exc:
            retryable = is_retryable(exc)
            if attempt >= max_attempts or not retryable:
                log_event(
                    "retry",
                    "warning",
                    "retry.stop",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    retryable=retryable,
                    error_type=type(exc).__name__,
                    error=exc,
                )
                raise

            delay = min(
                base_delay_seconds * (2 ** (attempt - 1)),
                max_delay_seconds,
            )
            log_event(
                "retry",
                "warning",
                "retry.scheduled",
                attempt=attempt,
                max_attempts=max_attempts,
                delay_seconds=delay,
                error_type=type(exc).__name__,
                error=exc,
            )
            await asyncio.sleep(delay)
