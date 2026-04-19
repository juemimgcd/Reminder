import sys
from collections.abc import Mapping

from loguru import logger

from conf.config import settings


def setup_logger() -> None:
    logger.remove()
    logger.configure(extra={"module": "app"})

    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL.upper(),
        enqueue=False,
        backtrace=False,
        diagnose=False,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level} | "
            "{extra[module]} | "
            "{message}"
        ),
    )


app_logger = logger


def _stringify_log_value(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    if isinstance(value, (list, tuple, set)):
        return "[" + ",".join(_stringify_log_value(item) for item in value) + "]"
    if isinstance(value, Mapping):
        return "{" + ",".join(
            f"{key}:{_stringify_log_value(item)}"
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        ) + "}"
    text = str(value)
    return text.replace("\n", "\\n")


def build_log_message(event: str, **fields) -> str:
    if not fields:
        return event

    rendered_fields = " ".join(
        f"{key}={_stringify_log_value(value)}"
        for key, value in fields.items()
    )
    return f"{event} {rendered_fields}"


def log_event(module: str, level: str, event: str, **fields) -> None:
    bound_logger = app_logger.bind(module=module)
    log_method = getattr(bound_logger, level.lower())
    log_method(build_log_message(event, **fields))


setup_logger()







