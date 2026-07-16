from typing import Any

from pydantic import ValidationError

from app.mneme.memoria.clients.memory_agent import MemoryAgentClient, MemoryAgentRejected
from app.mneme.memoria.schemas.memory_agent import MemoryAgentEvent
from app.mneme.models.outbox_event import OutboxEvent


async def apply_memory_agent_http_event(event: OutboxEvent) -> dict[str, Any]:
    try:
        envelope = MemoryAgentEvent.model_validate(event.payload)
    except ValidationError as exc:
        raise MemoryAgentRejected("invalid memory agent outbox envelope", status_code=422) from exc
    async with MemoryAgentClient() as client:
        receipt = await client.submit_event(envelope)
    return receipt.model_dump(mode="json")
