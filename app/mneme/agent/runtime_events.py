import json
import logging
import uuid
from collections import OrderedDict
from collections.abc import Iterable
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.mneme.agent.events import AgentEvent
from app.mneme.conf.config import settings

logger = logging.getLogger(__name__)


class RuntimeEventType(str, Enum):
    RUN_STARTED = "run.started"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    RUN_ABORTED = "run.aborted"
    CONTEXT_READY = "context.ready"
    CAPABILITY_PROJECTED = "capability.projected"
    LLM_REQUESTED = "llm.requested"
    LLM_COMPLETED = "llm.completed"
    LLM_FAILED = "llm.failed"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    PERSISTENCE_COMPLETED = "persistence.completed"
    PERSISTENCE_FAILED = "persistence.failed"


class RuntimeEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex}")
    event_type: RuntimeEventType
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: str
    run_id: str | None = None
    session_id: str | None = None
    user_id: int
    loop_index: int | None = None
    tool_call_id: str | None = None
    duration_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    error_kind: str | None = None
    selected_capability_ids: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class RuntimeEventSubscriber(Protocol):
    async def handle(self, event: RuntimeEvent) -> None: ...


class StructuredRuntimeLogger:
    async def handle(self, event: RuntimeEvent) -> None:
        logger.info(
            "agent_runtime_event %s",
            json.dumps(event.model_dump(mode="json"), ensure_ascii=False, sort_keys=True),
        )


class RuntimeMetricsCollector:
    def __init__(self, max_traces: int = 1000):
        self.max_traces = max(1, max_traces)
        self._traces: OrderedDict[str, dict[str, int]] = OrderedDict()

    async def handle(self, event: RuntimeEvent) -> None:
        metrics = self._traces.setdefault(event.trace_id, self._empty_metrics())
        self._traces.move_to_end(event.trace_id)
        while len(self._traces) > self.max_traces:
            self._traces.popitem(last=False)

        metrics["event_count"] += 1
        metrics["duration_ms"] += event.duration_ms or 0
        metrics["input_tokens"] += event.input_tokens or 0
        metrics["output_tokens"] += event.output_tokens or 0
        if event.event_type == RuntimeEventType.LLM_COMPLETED:
            metrics["model_calls"] += 1
            metrics["model_duration_ms"] += event.duration_ms or 0
        elif event.event_type in {
            RuntimeEventType.TOOL_COMPLETED,
            RuntimeEventType.TOOL_FAILED,
        }:
            metrics["tool_calls"] += 1
            metrics["tool_duration_ms"] += event.duration_ms or 0
        elif event.event_type in {
            RuntimeEventType.LLM_FAILED,
            RuntimeEventType.RUN_FAILED,
            RuntimeEventType.PERSISTENCE_FAILED,
        }:
            metrics["failure_count"] += 1

    def snapshot(self, trace_id: str) -> dict[str, int]:
        return dict(self._traces.get(trace_id, self._empty_metrics()))

    @staticmethod
    def _empty_metrics() -> dict[str, int]:
        return {
            "event_count": 0,
            "model_calls": 0,
            "tool_calls": 0,
            "failure_count": 0,
            "duration_ms": 0,
            "model_duration_ms": 0,
            "tool_duration_ms": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }


class RuntimeAuditSubscriber:
    async def handle(self, event: RuntimeEvent) -> None:
        from app.mneme.conf.database import open_write_session
        from app.mneme.models.agent_runtime_event import AgentRuntimeEvent

        async with open_write_session() as db:
            db.add(
                AgentRuntimeEvent(
                    id=event.event_id,
                    event_type=event.event_type.value,
                    occurred_at=event.occurred_at,
                    trace_id=event.trace_id,
                    run_id=event.run_id,
                    session_id=event.session_id,
                    user_id=event.user_id,
                    loop_index=event.loop_index,
                    tool_call_id=event.tool_call_id,
                    duration_ms=event.duration_ms,
                    input_tokens=event.input_tokens,
                    output_tokens=event.output_tokens,
                    error_kind=event.error_kind,
                    selected_capability_ids=event.selected_capability_ids,
                    payload=event.payload,
                )
            )


class RuntimeEventBus:
    def __init__(self, subscribers: Iterable[RuntimeEventSubscriber] = ()):
        self._subscribers = tuple(subscribers)

    async def publish(self, event: RuntimeEvent) -> None:
        for subscriber in self._subscribers:
            try:
                await subscriber.handle(event)
            except Exception as exc:
                logger.warning(
                    "runtime event subscriber failed subscriber=%s event_type=%s error=%s",
                    type(subscriber).__name__,
                    event.event_type.value,
                    type(exc).__name__,
                )


class RuntimeEventDispatcher:
    def __init__(
        self,
        *,
        trace_id: str,
        run_id: str | None,
        session_id: str | None,
        user_id: int,
        bus: RuntimeEventBus | None = None,
        metrics: RuntimeMetricsCollector | None = None,
    ):
        self.trace_id = trace_id
        self.run_id = run_id
        self.session_id = session_id
        self.user_id = user_id
        self._bus = bus or runtime_event_bus
        self._metrics = metrics or runtime_metrics

    async def emit(
        self,
        event_type: RuntimeEventType,
        *,
        loop_index: int | None = None,
        tool_call_id: str | None = None,
        duration_ms: int | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        error_kind: str | None = None,
        selected_capability_ids: list[str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> RuntimeEvent:
        event = RuntimeEvent(
            event_type=event_type,
            trace_id=self.trace_id,
            run_id=self.run_id,
            session_id=self.session_id,
            user_id=self.user_id,
            loop_index=loop_index,
            tool_call_id=tool_call_id,
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error_kind=error_kind,
            selected_capability_ids=selected_capability_ids or [],
            payload=payload or {},
        )
        await self._bus.publish(event)
        return event

    def metrics_snapshot(self) -> dict[str, int]:
        return self._metrics.snapshot(self.trace_id)


class RuntimeSseAdapter:
    @staticmethod
    def enrich(event: AgentEvent, runtime_event: RuntimeEvent) -> AgentEvent:
        metadata = {
            **event.metadata,
            "trace_id": runtime_event.trace_id,
            "run_id": runtime_event.run_id,
            "session_id": runtime_event.session_id,
            "user_id": runtime_event.user_id,
            "runtime_event_type": runtime_event.event_type.value,
            "selected_capability_ids": runtime_event.selected_capability_ids,
        }
        return event.model_copy(update={"metadata": metadata})


runtime_metrics = RuntimeMetricsCollector(settings.AGENT_RUNTIME_METRICS_MAX_TRACES)
_runtime_subscribers: list[RuntimeEventSubscriber] = [
    StructuredRuntimeLogger(),
    runtime_metrics,
]
if settings.AGENT_RUNTIME_AUDIT_ENABLED:
    _runtime_subscribers.append(RuntimeAuditSubscriber())
runtime_event_bus = RuntimeEventBus(_runtime_subscribers)
