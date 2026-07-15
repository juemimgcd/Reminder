import asyncio
from collections import defaultdict

from redis.asyncio import Redis

from app.mneme.agent.events import AgentEvent
from app.mneme.agent.run_models import AgentRunRecord, AgentStoredEvent
from app.mneme.conf.config import settings


class AgentRunStore:
    """Redis-backed ephemeral run state with a process-local development fallback."""

    def __init__(self) -> None:
        self._redis: Redis | None = None
        self._backend: str | None = None
        self._backend_lock = asyncio.Lock()
        self._memory_records: dict[str, AgentRunRecord] = {}
        self._memory_events: dict[str, list[AgentStoredEvent]] = defaultdict(list)
        self._memory_aborts: set[str] = set()

    async def create(self, record: AgentRunRecord) -> None:
        await self._ensure_backend()
        if self._backend == "redis":
            await self._save_redis_record(record)
            return
        self._memory_records[record.run_id] = record.model_copy(deep=True)

    async def get(self, run_id: str) -> AgentRunRecord | None:
        await self._ensure_backend()
        if self._backend == "redis":
            payload = await self._redis_client().get(self._record_key(run_id))
            return AgentRunRecord.model_validate_json(payload) if payload else None
        record = self._memory_records.get(run_id)
        return record.model_copy(deep=True) if record else None

    async def save(self, record: AgentRunRecord) -> None:
        await self._ensure_backend()
        if self._backend == "redis":
            await self._save_redis_record(record)
            return
        self._memory_records[record.run_id] = record.model_copy(deep=True)

    async def append_event(self, run_id: str, event: AgentEvent) -> AgentStoredEvent:
        await self._ensure_backend()
        if self._backend == "redis":
            client = self._redis_client()
            event_id = await client.xadd(
                self._events_key(run_id),
                {"event": event.model_dump_json()},
                maxlen=settings.AGENT_RUN_EVENT_MAXLEN,
                approximate=True,
            )
            await client.expire(self._events_key(run_id), settings.AGENT_RUN_TTL_SECONDS)
            stored = AgentStoredEvent(event_id=str(event_id), event=event)
        else:
            events = self._memory_events[run_id]
            stored = AgentStoredEvent(event_id=f"{len(events) + 1}-0", event=event)
            events.append(stored)

        record = await self.get(run_id)
        if record:
            record.last_event_id = stored.event_id
            await self.save(record)
        return stored

    async def list_events(self, run_id: str, *, after_id: str | None = None) -> list[AgentStoredEvent]:
        await self._ensure_backend()
        if self._backend == "redis":
            minimum = f"({after_id}" if after_id else "-"
            rows = await self._redis_client().xrange(self._events_key(run_id), min=minimum, max="+")
            return [
                AgentStoredEvent(event_id=str(event_id), event=AgentEvent.model_validate_json(fields["event"]))
                for event_id, fields in rows
            ]
        events = self._memory_events.get(run_id, [])
        if not after_id:
            return [item.model_copy(deep=True) for item in events]
        return [
            item.model_copy(deep=True)
            for item in events
            if _stream_id_number(item.event_id) > _stream_id_number(after_id)
        ]

    async def request_abort(self, run_id: str) -> None:
        await self._ensure_backend()
        if self._backend == "redis":
            await self._redis_client().set(
                self._abort_key(run_id), "1", ex=settings.AGENT_RUN_TTL_SECONDS
            )
            return
        self._memory_aborts.add(run_id)

    async def is_abort_requested(self, run_id: str) -> bool:
        await self._ensure_backend()
        if self._backend == "redis":
            return bool(await self._redis_client().exists(self._abort_key(run_id)))
        return run_id in self._memory_aborts

    async def _ensure_backend(self) -> None:
        if self._backend is not None:
            return
        async with self._backend_lock:
            if self._backend is not None:
                return
            client: Redis = Redis.from_url(
                settings.AGENT_RUN_REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=1.0,
            )
            try:
                await client.ping()
            except Exception:
                await client.aclose()
                self._backend = "memory"
            else:
                self._redis = client
                self._backend = "redis"

    async def _save_redis_record(self, record: AgentRunRecord) -> None:
        await self._redis_client().set(
            self._record_key(record.run_id),
            record.model_dump_json(),
            ex=settings.AGENT_RUN_TTL_SECONDS,
        )

    def _redis_client(self) -> Redis:
        if self._redis is None:
            raise RuntimeError("Redis run store is not initialized")
        return self._redis

    @staticmethod
    def _record_key(run_id: str) -> str:
        return f"mneme:agent-run:{run_id}:record"

    @staticmethod
    def _events_key(run_id: str) -> str:
        return f"mneme:agent-run:{run_id}:events"

    @staticmethod
    def _abort_key(run_id: str) -> str:
        return f"mneme:agent-run:{run_id}:abort"


def _stream_id_number(value: str) -> tuple[int, int]:
    major, _, minor = value.partition("-")
    return int(major), int(minor or 0)


agent_run_store = AgentRunStore()
