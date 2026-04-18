import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from conf.logging import app_logger


T = TypeVar("T")


# 对异步调用执行带可恢复错误判断的指数退避重试。
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
                app_logger.bind(module="retry").warning(
                    f"retry stop attempt={attempt}/{max_attempts} "
                    f"retryable={retryable} error_type={type(exc).__name__} error={exc}"
                )
                raise

            delay = min(
                base_delay_seconds * (2 ** (attempt - 1)),
                max_delay_seconds,
                )
            app_logger.bind(module="retry").warning(
                f"retry scheduled attempt={attempt}/{max_attempts} "
                f"delay_seconds={delay} error_type={type(exc).__name__} error={exc}"
            )
            await asyncio.sleep(delay)
