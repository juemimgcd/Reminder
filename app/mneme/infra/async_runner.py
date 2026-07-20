import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")

_task_loop: asyncio.AbstractEventLoop | None = None


def run_task_coroutine(coroutine: Coroutine[Any, Any, T]) -> T:
    global _task_loop

    if _task_loop is None or _task_loop.is_closed():
        _task_loop = asyncio.new_event_loop()
    return _task_loop.run_until_complete(coroutine)
