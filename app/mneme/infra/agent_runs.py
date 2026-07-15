import asyncio
import hashlib
import time
from collections import defaultdict, deque

from redis.asyncio import Redis

from app.mneme.agent.events import AgentEvent
from app.mneme.agent.run_models import (
    TERMINAL_AGENT_RUN_STATUSES,
    AgentRunRecord,
    AgentRunStatus,
    AgentStoredEvent,
)
from app.mneme.conf.config import settings


class AgentRunStore:
    """Redis-backed ephemeral run state with a process-local development fallback."""

    def __init__(self) -> None:
        self._redis: Redis | None = None
        self._backend: str | None = None
        self._backend_lock = asyncio.Lock()
        self._memory_lock = asyncio.Lock()
        self._memory_records: dict[str, AgentRunRecord] = {}
        self._memory_events: dict[str, list[AgentStoredEvent]] = defaultdict(list)
        self._memory_aborts: set[str] = set()
        self._memory_request_runs: dict[str, str] = {}
        self._memory_session_queues: dict[str, deque[str]] = defaultdict(deque)
        self._memory_session_leases: dict[str, tuple[str, float]] = {}

    async def create(self, record: AgentRunRecord) -> None:
        await self._ensure_backend()
        if self._backend == "redis":
            await self._save_redis_record(record)
            return
        self._memory_records[record.run_id] = record.model_copy(deep=True)

    async def create_or_get_and_enqueue(
        self,
        record: AgentRunRecord,
    ) -> tuple[AgentRunRecord, bool]:
        """Atomically create one run per client request and append it to the session FIFO."""
        await self._ensure_backend()
        request_key = self._request_key(
            record.user_id,
            record.session_id,
            record.client_request_id,
        )
        if self._backend == "redis":
            result = await self._redis_client().eval(
                _CREATE_AND_ENQUEUE_SCRIPT,
                3,
                self._record_key(record.run_id),
                request_key,
                self._session_queue_key(record.session_id),
                record.model_dump_json(),
                record.run_id,
                settings.AGENT_RUN_TTL_SECONDS,
            )
            run_id, created_flag = str(result[0]), str(result[1])
            if created_flag == "1":
                return record.model_copy(deep=True), True
            existing = await self.get(run_id)
            if existing is None:
                raise RuntimeError("idempotent agent run record expired unexpectedly")
            return existing, False

        async with self._memory_lock:
            existing_run_id = self._memory_request_runs.get(request_key)
            if existing_run_id:
                existing = self._memory_records.get(existing_run_id)
                if existing:
                    return existing.model_copy(deep=True), False
            self._memory_records[record.run_id] = record.model_copy(deep=True)
            self._memory_request_runs[request_key] = record.run_id
            self._memory_session_queues[record.session_id].append(record.run_id)
            return record.model_copy(deep=True), True

    async def claim_session_turn(
        self,
        *,
        session_id: str,
        run_id: str,
        lease_token: str,
    ) -> bool:
        await self._ensure_backend()
        if self._backend == "redis":
            claimed = await self._redis_client().eval(
                _CLAIM_SESSION_SCRIPT,
                2,
                self._session_queue_key(session_id),
                self._session_lease_key(session_id),
                run_id,
                lease_token,
                int(settings.AGENT_SESSION_LEASE_SECONDS * 1000),
            )
            return bool(int(claimed))

        async with self._memory_lock:
            queue = self._memory_session_queues[session_id]
            if not queue or queue[0] != run_id:
                return False
            current = self._memory_session_leases.get(session_id)
            now = time.monotonic()
            if current and current[1] > now and current[0] != lease_token:
                return False
            self._memory_session_leases[session_id] = (
                lease_token,
                now + settings.AGENT_SESSION_LEASE_SECONDS,
            )
            return True

    async def enqueue_session_turn(self, *, session_id: str, ticket_id: str) -> None:
        await self._ensure_backend()
        if self._backend == "redis":
            client = self._redis_client()
            await client.rpush(self._session_queue_key(session_id), ticket_id)
            await client.expire(
                self._session_queue_key(session_id),
                settings.AGENT_RUN_TTL_SECONDS,
            )
            return
        async with self._memory_lock:
            self._memory_session_queues[session_id].append(ticket_id)

    async def renew_session_lease(self, *, session_id: str, lease_token: str) -> bool:
        await self._ensure_backend()
        if self._backend == "redis":
            renewed = await self._redis_client().eval(
                _RENEW_SESSION_SCRIPT,
                1,
                self._session_lease_key(session_id),
                lease_token,
                int(settings.AGENT_SESSION_LEASE_SECONDS * 1000),
            )
            return bool(int(renewed))

        async with self._memory_lock:
            current = self._memory_session_leases.get(session_id)
            if not current or current[0] != lease_token:
                return False
            self._memory_session_leases[session_id] = (
                lease_token,
                time.monotonic() + settings.AGENT_SESSION_LEASE_SECONDS,
            )
            return True

    async def release_session_turn(
        self,
        *,
        session_id: str,
        run_id: str,
        lease_token: str,
    ) -> None:
        await self._ensure_backend()
        if self._backend == "redis":
            await self._redis_client().eval(
                _RELEASE_SESSION_SCRIPT,
                2,
                self._session_queue_key(session_id),
                self._session_lease_key(session_id),
                run_id,
                lease_token,
                settings.AGENT_RUN_TTL_SECONDS,
            )
            return

        async with self._memory_lock:
            current = self._memory_session_leases.get(session_id)
            if current and current[0] != lease_token:
                return
            if current:
                self._memory_session_leases.pop(session_id, None)
            queue = self._memory_session_queues.get(session_id)
            if queue:
                try:
                    queue.remove(run_id)
                except ValueError:
                    pass
                if not queue:
                    self._memory_session_queues.pop(session_id, None)

    async def remove_from_session_queue(self, *, session_id: str, run_id: str) -> None:
        await self._ensure_backend()
        if self._backend == "redis":
            await self._redis_client().lrem(self._session_queue_key(session_id), 1, run_id)
            return
        async with self._memory_lock:
            queue = self._memory_session_queues.get(session_id)
            if not queue:
                return
            try:
                queue.remove(run_id)
            except ValueError:
                return
            if not queue:
                self._memory_session_queues.pop(session_id, None)

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

    async def transition_to_aborting(self, run_id: str) -> AgentRunRecord | None:
        """Set abort intent without allowing a stale writer to regress a terminal run."""
        await self._ensure_backend()
        if self._backend == "redis":
            payload = await self._redis_client().eval(
                _TRANSITION_TO_ABORTING_SCRIPT,
                2,
                self._record_key(run_id),
                self._abort_key(run_id),
                settings.AGENT_RUN_TTL_SECONDS,
            )
            return AgentRunRecord.model_validate_json(payload) if payload else None
        async with self._memory_lock:
            record = self._memory_records.get(run_id)
            if record is None:
                return None
            if record.status not in TERMINAL_AGENT_RUN_STATUSES:
                record = record.model_copy(update={"status": AgentRunStatus.ABORTING})
                self._memory_records[run_id] = record
                self._memory_aborts.add(run_id)
            return record.model_copy(deep=True)

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

    @staticmethod
    def _request_key(user_id: int, session_id: str, client_request_id: str) -> str:
        digest = hashlib.sha256(
            f"{user_id}:{session_id}:{client_request_id}".encode("utf-8")
        ).hexdigest()
        return f"mneme:agent-request:{digest}"

    @staticmethod
    def _session_queue_key(session_id: str) -> str:
        return f"mneme:agent-session:{session_id}:queue"

    @staticmethod
    def _session_lease_key(session_id: str) -> str:
        return f"mneme:agent-session:{session_id}:lease"


def _stream_id_number(value: str) -> tuple[int, int]:
    major, _, minor = value.partition("-")
    return int(major), int(minor or 0)


agent_run_store = AgentRunStore()


_CREATE_AND_ENQUEUE_SCRIPT = """
local existing = redis.call('GET', KEYS[2])
if existing then
  return {existing, '0'}
end
redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[3])
redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3])
redis.call('RPUSH', KEYS[3], ARGV[2])
redis.call('EXPIRE', KEYS[3], ARGV[3])
return {ARGV[2], '1'}
"""


_TRANSITION_TO_ABORTING_SCRIPT = """
local payload = redis.call('GET', KEYS[1])
if not payload then
  return nil
end
local record = cjson.decode(payload)
if record.status ~= 'completed' and record.status ~= 'failed' and record.status ~= 'aborted' then
  record.status = 'aborting'
  payload = cjson.encode(record)
  redis.call('SET', KEYS[1], payload, 'EX', ARGV[1])
  redis.call('SET', KEYS[2], '1', 'EX', ARGV[1])
end
return payload
"""


_CLAIM_SESSION_SCRIPT = """
local head = redis.call('LINDEX', KEYS[1], 0)
if head ~= ARGV[1] then
  return 0
end
local owner = redis.call('GET', KEYS[2])
if not owner then
  if redis.call('SET', KEYS[2], ARGV[2], 'NX', 'PX', ARGV[3]) then
    return 1
  end
  return 0
end
if owner == ARGV[2] then
  redis.call('PEXPIRE', KEYS[2], ARGV[3])
  return 1
end
return 0
"""


_RENEW_SESSION_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  redis.call('PEXPIRE', KEYS[1], ARGV[2])
  return 1
end
return 0
"""


_RELEASE_SESSION_SCRIPT = """
local owner = redis.call('GET', KEYS[2])
if owner and owner ~= ARGV[2] then
  return 0
end
if owner == ARGV[2] then
  redis.call('DEL', KEYS[2])
end
redis.call('LREM', KEYS[1], 1, ARGV[1])
if redis.call('LLEN', KEYS[1]) > 0 then
  redis.call('EXPIRE', KEYS[1], ARGV[3])
else
  redis.call('DEL', KEYS[1])
end
return 1
"""
