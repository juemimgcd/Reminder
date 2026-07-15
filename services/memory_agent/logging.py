import logging

from services.memory_agent.observability.context import SafeJsonFormatter


def _handler() -> logging.Handler:
    handler = logging.StreamHandler()
    handler.setFormatter(SafeJsonFormatter())
    return handler


def configure_logger(logger: logging.Logger) -> None:
    logger.handlers.clear()
    logger.addHandler(_handler())
    logger.setLevel(logging.INFO)
    logger.propagate = False


def configure_logging() -> None:
    root = logging.getLogger()
    configure_logger(root)
    root.propagate = True
    for name in ("uvicorn", "uvicorn.error"):
        configure_logger(logging.getLogger(name))
    access = logging.getLogger("uvicorn.access")
    access.handlers.clear()
    access.disabled = True
