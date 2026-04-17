import sys
from loguru import logger


def setup_logger() -> None:
    logger.remove()

    logger.add(
        sys.stdout,
        level="INFO",
        enqueue=True,
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



































