import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

from app.mneme.domains.tasks.outbox import build_outbox_idempotency_key
from app.mneme.memoria.automation import outbox as automation_outbox
from app.mneme.memoria.automation import service as automation_service
from app.mneme.memoria.subscribers.contracts import RuntimeSubscriberEvent, SubscriberAction
from app.mneme.memoria.subscribers.dispatcher import dispatch_runtime_subscribers
from app.mneme.memoria.subscribers.registry import RuntimeSubscriberRegistry


class _Subscriber:
    def __init__(self, name, event_types, handler, *, timeout_seconds=0.1):
        self.name = name
        self.event_types = frozenset(event_types)
        self.timeout_seconds = timeout_seconds
        self._handler = handler

    async def handle(self, event):
        return await self._handler(event)


def _event(**updates):
    values = {
        "event_id": "outbox-1",
        "event_type": "conversation.completed",
        "user_id": 7,
        "run_id": "run-1",
        "idempotency_key": "conversation.completed:conversation:session-1:operation-1",
        "payload": {"session_id": "session-1"},
    }
    values.update(updates)
    return RuntimeSubscriberEvent(**values)


async def _no_actions(event):
    return []


async def _apply_action(**kwargs):
    return {"idempotency_key": kwargs["idempotency_key"]}


def test_only_explicitly_subscribed_event_types_are_delivered():
    calls = []

    async def observe(name, event):
        calls.append((name, event.event_type))
        return []

    registry = RuntimeSubscriberRegistry(
        [
            _Subscriber("conversation", {"conversation.completed"}, lambda event: observe("conversation", event)),
            _Subscriber("profile", {"profile.updated"}, lambda event: observe("profile", event)),
        ]
    )

    results = asyncio.run(
        dispatch_runtime_subscribers(_event(), registry=registry, apply_action=_apply_action)
    )

    assert calls == [("conversation", "conversation.completed")]
    assert [result.subscriber_name for result in results] == ["conversation"]


def test_handler_receives_scoped_identity_and_sanitized_payload():
    received = []

    async def capture(event):
        received.append(event)
        return []

    registry = RuntimeSubscriberRegistry(
        [_Subscriber("capture", {"conversation.completed"}, capture)]
    )
    event = _event(
        payload={
            "session_id": "session-1",
            "api_key": "sk-abcdefghijklmnopqrstuvwxyz",
            "nested": {"provider": "Bearer abcdefghijklmnopqrstuvwxyz"},
        }
    )

    asyncio.run(dispatch_runtime_subscribers(event, registry=registry, apply_action=_apply_action))

    delivered = received[0]
    assert delivered.event_id == "outbox-1"
    assert delivered.event_type == "conversation.completed"
    assert delivered.user_id == 7
    assert delivered.run_id == "run-1"
    assert delivered.idempotency_key == event.idempotency_key
    assert delivered.payload == {
        "session_id": "session-1",
        "api_key": "[REDACTED]",
        "nested": {"provider": "[REDACTED]"},
    }


def test_duplicate_delivery_uses_one_logical_action_identity():
    applied = {}

    async def propose(event):
        return [SubscriberAction(type="send_notification", payload={"title": "Review"})]

    async def apply_once(**kwargs):
        key = kwargs["idempotency_key"]
        applied.setdefault(key, kwargs["action"])
        return {"idempotency_key": key}

    registry = RuntimeSubscriberRegistry(
        [_Subscriber("review", {"conversation.completed"}, propose)]
    )
    event = _event()

    first = asyncio.run(
        dispatch_runtime_subscribers(event, registry=registry, apply_action=apply_once)
    )
    second = asyncio.run(
        dispatch_runtime_subscribers(event, registry=registry, apply_action=apply_once)
    )

    assert len(applied) == 1
    assert next(iter(applied)) == f"{event.idempotency_key}:review:0"
    assert first[0].status == second[0].status == "succeeded"


def test_action_idempotency_key_is_stable_and_storage_bounded():
    keys = []

    async def propose(event):
        return [SubscriberAction(type="send_notification", payload={"title": "Review"})]

    async def capture(**kwargs):
        keys.append(kwargs["idempotency_key"])
        return {}

    registry = RuntimeSubscriberRegistry(
        [_Subscriber("review", {"conversation.completed"}, propose)]
    )
    event = _event(idempotency_key="outbox-" + "x" * 193)

    asyncio.run(dispatch_runtime_subscribers(event, registry=registry, apply_action=capture))
    asyncio.run(dispatch_runtime_subscribers(event, registry=registry, apply_action=capture))

    assert keys[0] == keys[1]
    assert keys[0].startswith("outbox-")
    assert len(keys[0]) <= 200


def test_failure_and_timeout_do_not_skip_later_subscribers():
    calls = []

    async def fail(event):
        calls.append("fail")
        raise RuntimeError("provider response with a secret")

    async def wait(event):
        calls.append("wait")
        await asyncio.sleep(0.05)
        return []

    async def finish(event):
        calls.append("finish")
        return []

    registry = RuntimeSubscriberRegistry(
        [
            _Subscriber("failure", {"conversation.completed"}, fail),
            _Subscriber("timeout", {"conversation.completed"}, wait, timeout_seconds=0.001),
            _Subscriber("success", {"conversation.completed"}, finish),
        ]
    )

    results = asyncio.run(
        dispatch_runtime_subscribers(_event(), registry=registry, apply_action=_apply_action)
    )

    assert calls == ["fail", "wait", "finish"]
    assert [result.status for result in results] == ["failed", "timed_out", "succeeded"]
    assert [result.error_type for result in results] == ["RuntimeError", "TimeoutError", None]
    assert "secret" not in " ".join(result.model_dump_json() for result in results)


def test_unsupported_subscriber_action_is_rejected():
    applied = []

    async def unsupported(event):
        return [{"type": "run_shell", "payload": {"command": "whoami"}}]

    async def capture(**kwargs):
        applied.append(kwargs)
        return {}

    registry = RuntimeSubscriberRegistry(
        [_Subscriber("unsupported", {"conversation.completed"}, unsupported)]
    )

    results = asyncio.run(
        dispatch_runtime_subscribers(_event(), registry=registry, apply_action=capture)
    )

    assert applied == []
    assert results[0].status == "rejected"
    assert results[0].error_type == "UnsupportedAction"


def test_subscriber_action_cannot_target_another_user():
    applied = []

    async def cross_user(event):
        return [
            SubscriberAction(
                type="send_notification",
                payload={"user_id": event.user_id + 1, "title": "Wrong owner"},
            )
        ]

    async def capture(**kwargs):
        applied.append(kwargs)
        return {}

    registry = RuntimeSubscriberRegistry(
        [_Subscriber("cross-user", {"conversation.completed"}, cross_user)]
    )

    results = asyncio.run(
        dispatch_runtime_subscribers(_event(), registry=registry, apply_action=capture)
    )

    assert applied == []
    assert results[0].status == "rejected"
    assert results[0].error_type == "UserScopeViolation"


def test_internal_hook_dispatches_subscribers_and_existing_heartbeats(monkeypatch):
    delivered = []
    action_calls = []

    async def capture(event):
        delivered.append(event)
        return [SubscriberAction(type="send_notification", payload={"title": "Review"})]

    registry = RuntimeSubscriberRegistry(
        [_Subscriber("capture", {"conversation.completed"}, capture)]
    )
    db = object()
    job = SimpleNamespace(id="heartbeat-1")
    run = SimpleNamespace(run_id="heartbeat-run-1")

    @asynccontextmanager
    async def open_session():
        yield db

    async def apply_action(**kwargs):
        action_calls.append(kwargs)
        return {"notification_id": "notification-1"}

    monkeypatch.setattr(automation_outbox, "runtime_subscriber_registry", registry)
    monkeypatch.setattr(automation_outbox, "open_write_session", open_session)
    monkeypatch.setattr(automation_outbox, "apply_runtime_subscriber_action", apply_action)
    monkeypatch.setattr(
        automation_outbox,
        "list_event_heartbeat_jobs",
        lambda db, **kwargs: asyncio.sleep(0, result=[job]),
    )
    monkeypatch.setattr(
        automation_outbox,
        "get_heartbeat_job",
        lambda db, **kwargs: asyncio.sleep(0, result=job),
    )
    monkeypatch.setattr(
        automation_outbox,
        "dispatch_heartbeat_job",
        lambda db, **kwargs: asyncio.sleep(0, result=run),
    )
    outbox_event = SimpleNamespace(
        id="outbox-1",
        event_type="conversation.completed",
        idempotency_key="conversation.completed:conversation:session-1:operation-1",
        payload={
            "user_id": 7,
            "run_id": "run-1",
            "session_id": "session-1",
            "api_key": "sk-abcdefghijklmnopqrstuvwxyz",
        },
    )

    result = asyncio.run(automation_outbox.apply_internal_hook_event(outbox_event))

    assert delivered[0].user_id == 7
    assert delivered[0].run_id == "run-1"
    assert delivered[0].payload["api_key"] == "[REDACTED]"
    assert action_calls[0]["db"] is db
    assert result["dispatched_run_ids"] == ["heartbeat-run-1"]
    assert result["subscriber_results"][0]["status"] == "succeeded"


def test_create_approval_action_uses_scoped_idempotent_service(monkeypatch):
    captured = {}

    async def create_approval(db, **values):
        captured.update(values)
        return SimpleNamespace(id="approval-1", user_id=values["user_id"])

    monkeypatch.setattr(automation_service, "create_or_get_tool_approval", create_approval)
    result = asyncio.run(
        automation_service.apply_runtime_subscriber_action(
            db=object(),
            event=_event(),
            subscriber_name="review",
            action=SubscriberAction(
                type="create_approval",
                payload={
                    "action_name": "memory_review.propose",
                    "summary": "Review this memory",
                    "arguments": {"memory_id": "memory-1"},
                },
            ),
            idempotency_key="outbox-key:review:0",
        )
    )

    assert captured["user_id"] == 7
    assert captured["run_id"] == "run-1"
    assert captured["idempotency_key"] == "outbox-key:review:0"
    assert len(captured["id"]) <= 64
    assert result == {"approval_id": "approval-1", "user_id": 7}


def test_send_notification_action_uses_scoped_idempotent_service(monkeypatch):
    captured = {}

    async def create_notification(db, **values):
        captured.update(values)
        return SimpleNamespace(id="notification-1", user_id=values["user_id"])

    monkeypatch.setattr(
        automation_service,
        "create_notification_if_missing",
        create_notification,
    )
    result = asyncio.run(
        automation_service.apply_runtime_subscriber_action(
            db=object(),
            event=_event(),
            subscriber_name="review",
            action=SubscriberAction(
                type="send_notification",
                payload={"title": "Review", "body": "A memory needs review"},
            ),
            idempotency_key="outbox-key:review:0",
        )
    )

    assert captured["user_id"] == 7
    assert captured["idempotency_key"] == "outbox-key:review:0"
    assert len(captured["notification_id"]) <= 64
    assert captured["metadata"] == {"subscriber_name": "review"}
    assert result == {"notification_id": "notification-1", "user_id": 7}


def test_context_candidate_action_enqueues_governed_memory_event(monkeypatch):
    captured = {}

    async def enqueue(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id="outbox-candidate-1")

    monkeypatch.setattr(automation_service, "enqueue_outbox_event", enqueue)
    result = asyncio.run(
        automation_service.apply_runtime_subscriber_action(
            db=object(),
            event=_event(),
            subscriber_name="review",
            action=SubscriberAction(
                type="add_context_candidate",
                payload={
                    "knowledge_base_id": "kb-1",
                    "session_id": "session-1",
                    "message_id": "message-1",
                    "excerpt": "User explicitly asked to remember this.",
                },
            ),
            idempotency_key="outbox-key:review:0",
        )
    )

    assert captured["target_backend"] == "memory_agent_http"
    assert captured["operation_id"] == "outbox-key:review:0"
    assert len(captured["aggregate_id"]) <= 64
    assert captured["payload"]["owner_id"] == 7
    assert captured["payload"]["event_type"] == "user.memory_requested"
    assert captured["payload"]["payload"]["excerpt"] == "User explicitly asked to remember this."
    assert result == {"outbox_event_id": "outbox-candidate-1", "user_id": 7}


def test_context_candidate_nested_outbox_key_fits_storage(monkeypatch):
    captured = {}

    async def enqueue(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id="outbox-candidate-1")

    monkeypatch.setattr(automation_service, "enqueue_outbox_event", enqueue)
    asyncio.run(
        automation_service.apply_runtime_subscriber_action(
            db=object(),
            event=_event(),
            subscriber_name="review",
            action=SubscriberAction(
                type="add_context_candidate",
                payload={
                    "knowledge_base_id": "kb-1",
                    "session_id": "session-1",
                    "message_id": "message-1",
                    "excerpt": "Remember this.",
                },
            ),
            idempotency_key="outbox-" + "x" * 193,
        )
    )

    nested_key = build_outbox_idempotency_key(
        event_type=captured["event_type"],
        aggregate_type=captured["aggregate_type"],
        aggregate_id=captured["aggregate_id"],
        operation_id=captured["operation_id"],
    )
    assert len(nested_key) <= 200
