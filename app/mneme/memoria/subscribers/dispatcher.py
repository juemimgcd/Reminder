import asyncio
import hashlib
import time
from typing import Any, Protocol

from pydantic import ValidationError

from app.mneme.domains.tasks.outbox import _contains_secret
from app.mneme.memoria.subscribers.contracts import (
    RuntimeSubscriberEvent,
    SubscriberAction,
    SubscriberDispatchResult,
)
from app.mneme.memoria.subscribers.registry import RuntimeSubscriberRegistry

_REDACTED = "[REDACTED]"
_SECRET_KEYS = frozenset(
    {
        "api_key",
        "access_token",
        "auth_token",
        "bearer_token",
        "client_secret",
        "confirmation_token",
        "password",
        "private_key",
        "refresh_token",
        "secret",
        "token",
    }
)


class SubscriberActionApplier(Protocol):
    async def __call__(
        self,
        *,
        event: RuntimeSubscriberEvent,
        subscriber_name: str,
        action: SubscriberAction,
        idempotency_key: str,
    ) -> dict[str, Any]: ...


class _UnsupportedActionError(Exception):
    pass


class _UserScopeViolationError(Exception):
    pass


async def dispatch_runtime_subscribers(
    event: RuntimeSubscriberEvent,
    *,
    registry: RuntimeSubscriberRegistry,
    apply_action: SubscriberActionApplier,
) -> list[SubscriberDispatchResult]:
    sanitized_event = event.model_copy(update={"payload": sanitize_event_payload(event.payload)})
    results: list[SubscriberDispatchResult] = []
    for subscriber in registry.subscribers_for(event.event_type):
        started = time.perf_counter()
        try:
            async with asyncio.timeout(subscriber.timeout_seconds):
                raw_actions = await subscriber.handle(sanitized_event)
            actions = _validated_actions(raw_actions, user_id=event.user_id)
            for index, action in enumerate(actions):
                await apply_action(
                    event=sanitized_event,
                    subscriber_name=subscriber.name,
                    action=action,
                    idempotency_key=_action_idempotency_key(
                        event.idempotency_key,
                        subscriber.name,
                        index,
                    ),
                )
        except TimeoutError:
            results.append(
                _result(
                    subscriber.name,
                    "timed_out",
                    started,
                    error_type="TimeoutError",
                )
            )
        except _UnsupportedActionError:
            results.append(
                _result(
                    subscriber.name,
                    "rejected",
                    started,
                    error_type="UnsupportedAction",
                )
            )
        except _UserScopeViolationError:
            results.append(
                _result(
                    subscriber.name,
                    "rejected",
                    started,
                    error_type="UserScopeViolation",
                )
            )
        except Exception as exc:
            results.append(
                _result(
                    subscriber.name,
                    "failed",
                    started,
                    error_type=type(exc).__name__,
                )
            )
        else:
            results.append(
                _result(
                    subscriber.name,
                    "succeeded",
                    started,
                    action_count=len(actions),
                )
            )
    return results


def sanitize_event_payload(value: Any, *, key: str | None = None) -> Any:
    if key is not None and key.lower().replace("-", "_") in _SECRET_KEYS:
        return _REDACTED
    if isinstance(value, str):
        return _REDACTED if _contains_secret(value) else value
    if isinstance(value, dict):
        return {
            item_key: sanitize_event_payload(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [sanitize_event_payload(item) for item in value]
    return value


def _validated_actions(raw_actions: object, *, user_id: int) -> list[SubscriberAction]:
    if not isinstance(raw_actions, list):
        raise _UnsupportedActionError
    try:
        actions = [SubscriberAction.model_validate(action) for action in raw_actions]
    except ValidationError as exc:
        raise _UnsupportedActionError from exc
    for action in actions:
        target_user_id = action.payload.get("user_id")
        if target_user_id is not None and target_user_id != user_id:
            raise _UserScopeViolationError
    return actions


def _result(
    subscriber_name: str,
    status: str,
    started: float,
    *,
    action_count: int = 0,
    error_type: str | None = None,
) -> SubscriberDispatchResult:
    return SubscriberDispatchResult(
        subscriber_name=subscriber_name,
        status=status,
        duration_ms=max(0, int((time.perf_counter() - started) * 1000)),
        action_count=action_count,
        error_type=error_type,
    )


def _action_idempotency_key(outbox_key: str, subscriber_name: str, index: int) -> str:
    value = f"{outbox_key}:{subscriber_name}:{index}"
    if len(value) <= 200:
        return value
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]
    return f"{value[:167]}:{digest}"
