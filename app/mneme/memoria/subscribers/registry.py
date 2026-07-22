from collections.abc import Iterable

from app.mneme.memoria.subscribers.contracts import RuntimeSubscriber


class RuntimeSubscriberRegistry:
    def __init__(
        self,
        subscribers: Iterable[RuntimeSubscriber] = (),
        *,
        enabled_names: frozenset[str] | None = None,
    ) -> None:
        self._subscribers: dict[str, RuntimeSubscriber] = {}
        self._enabled_names = enabled_names
        for subscriber in subscribers:
            self.register(subscriber)

    def register(self, subscriber: RuntimeSubscriber) -> None:
        if not subscriber.name or subscriber.name in self._subscribers:
            raise ValueError("subscriber names must be non-empty and unique")
        if not subscriber.event_types or subscriber.timeout_seconds <= 0:
            raise ValueError("subscriber event types and timeout must be configured")
        self._subscribers[subscriber.name] = subscriber

    def subscribers_for(self, event_type: str) -> tuple[RuntimeSubscriber, ...]:
        return tuple(
            subscriber
            for subscriber in self._subscribers.values()
            if event_type in subscriber.event_types
            and (self._enabled_names is None or subscriber.name in self._enabled_names)
        )


runtime_subscriber_registry = RuntimeSubscriberRegistry()
