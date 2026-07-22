# Exception boundary contract

Mneme uses broad exception catches only at boundaries that must translate,
record, isolate, or clean up a failure. Domain code should catch the narrowest
exception it can recover from and otherwise let the original exception reach
one of these boundaries.

## Allowed boundary categories

| Category | Required behavior | Representative locations |
| --- | --- | --- |
| Transaction boundary | Roll back an active transaction and re-raise the original exception | `conf/database.py`, `memoria/server/database.py` |
| Durable worker boundary | Persist terminal failure state, emit correlation data, then re-raise so Celery records failure | `tasks/index_tasks.py`, `tasks/maintenance_tasks.py`, `memoria/run_service.py` |
| External dependency adapter | Classify retryability, update circuit state, remove secret-bearing details, and raise a stable application error | `clients/vector_store_client.py`, `memoria/server/providers/llm.py`, `memoria/server/memory/extraction.py` |
| Batch isolation boundary | Allow remaining independent items to run, increment a failure result, and rely on the per-item function to persist/log the failure | `domains/tasks/outbox.py`, `channels/delivery.py` |
| Cleanup boundary | Suppress only close/unlink cleanup failures after the primary result is fixed; never replace the primary exception | provider client `close()` paths and upload cleanup |
| HTTP boundary | Record a sanitized event with request/trace IDs and return or re-raise through the framework handler | shared HTTP observability middleware and API exception handlers |

## Invariants

Every `except Exception` must satisfy all applicable rules:

1. `asyncio.CancelledError`, process-exit signals, and framework cancellation
   semantics are never converted to normal success.
2. A durable operation records `failed`, retry/dead-letter state, and a bounded
   error code before control leaves the boundary.
3. Logs contain identifiers and exception type/error code, not document text,
   prompts, tokens, credentials, connection URLs, or raw provider responses.
4. A retry decision is explicit and bounded. The catch must not create an
   unbounded retry loop.
5. Cleanup suppression is limited to cleanup. Empty `pass` blocks are not valid
   around business, persistence, retrieval, or delivery operations.
6. Batch isolation returns an explicit failed count or status; it never reports
   full success after an item failed.
7. The original exception is chained when translation is useful and suppressed
   only when the stable public error intentionally hides sensitive internals.

## Audit result

The current tree contains broad catches mainly in the categories above. The
highest-risk areas are the durable run/outbox dispatchers and external model or
vector adapters; their catches already persist failure state or classify the
dependency before returning. Cleanup-only suppression exists around provider
client close operations and does not change the primary result.

Future changes should reject these patterns during review:

- `except Exception: pass` around a business operation;
- converting a dependency failure into an empty answer or empty retrieval set
  without a documented degraded-mode contract;
- logging `str(exc)` when the dependency may include credentials or payloads;
- incrementing a batch failure count before the per-item operation has recorded
  durable failure state;
- catching cancellation and continuing a worker lease or request as if it
  completed.

This document defines review rules rather than an allowlist of line numbers, so
the contract remains valid as modules move.
