# Runtime Contracts

This document records stable runtime invariants enforced by the running code.

## Durable internal subscribers

Internal runtime subscribers are code-owned objects registered in a process-local registry. The default registry is empty. Configuration may select registered names, but cannot provide Python import paths, executable commands, or scripts.

Only explicitly subscribed event types are delivered. Each handler receives the Outbox event identity, event type, owning user, optional run identity, the Outbox idempotency key, and a recursively sanitized payload. Secrets and credential-bearing values are replaced before handler invocation.

Handlers execute independently under their configured timeout. A failure, timeout, invalid action, or user-scope violation produces a stable result containing the handler name, status, duration, action count, and error type; exception messages are not retained. Later handlers and existing event-triggered heartbeat jobs still run.

Supported actions are limited to `create_approval`, `add_context_candidate`, and `send_notification`. Actions cannot target a user other than the event owner. They are applied through the existing approval, governed-memory event, and notification services with an idempotency key prefixed by the originating Outbox key and subscriber name. Handlers never write database rows directly.
