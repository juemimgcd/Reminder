import asyncio

from app.mneme.channels.contracts import NormalizedInboundMessage
from app.mneme.channels.delivery import (
    dispatch_channel_deliveries,
    process_channel_delivery,
)
from app.mneme.channels.inbound import process_inbound_message
from app.mneme.conf.logging import app_logger
from app.mneme.infra.celery_app import celery_app


@celery_app.task(name="tasks.process_channel_inbound_task")
def process_channel_inbound_task(*, message_payload: dict) -> None:
    message = NormalizedInboundMessage.model_validate(message_payload)
    receipt = asyncio.run(process_inbound_message(message))
    app_logger.bind(module="channel_inbound").info(
        f"channel inbound processed message_id={receipt.message_id} "
        f"status={receipt.status} run_id={receipt.run_id or ''}"
    )


@celery_app.task(name="tasks.process_channel_delivery_task")
def process_channel_delivery_task(*, delivery_id: str) -> None:
    app_logger.bind(module="channel_delivery").info(
        f"channel delivery start delivery_id={delivery_id}"
    )
    asyncio.run(process_channel_delivery(delivery_id))


@celery_app.task(name="tasks.dispatch_channel_deliveries_task")
def dispatch_channel_deliveries_task() -> None:
    result = asyncio.run(dispatch_channel_deliveries())
    app_logger.bind(module="channel_delivery").info(
        "channel delivery dispatch completed "
        f"matched={result['matched']} dispatched={result['dispatched']} "
        f"failed={result['failed']}"
    )
