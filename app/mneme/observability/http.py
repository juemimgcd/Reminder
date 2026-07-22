from collections.abc import Callable
from threading import Lock
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request

from app.mneme.observability.context import observation_context, safe_identifier

EventEmitter = Callable[..., None]
RequestKey = tuple[str, str, int]
DurationKey = tuple[str, str]


class HttpMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._requests: dict[RequestKey, int] = {}
        self._duration_count: dict[DurationKey, int] = {}
        self._duration_sum: dict[DurationKey, float] = {}

    def observe(self, *, method: str, route: str, status: int, duration_ms: float) -> None:
        request_key = (method, route, status)
        duration_key = (method, route)
        with self._lock:
            self._requests[request_key] = self._requests.get(request_key, 0) + 1
            self._duration_count[duration_key] = self._duration_count.get(duration_key, 0) + 1
            self._duration_sum[duration_key] = self._duration_sum.get(duration_key, 0.0) + duration_ms

    def snapshot(self) -> tuple[dict[RequestKey, int], dict[DurationKey, int], dict[DurationKey, float]]:
        with self._lock:
            return (
                self._requests.copy(),
                self._duration_count.copy(),
                self._duration_sum.copy(),
            )


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _metric_labels(**values: str) -> str:
    return "{" + ",".join(f'{key}="{_escape_label(value)}"' for key, value in values.items()) + "}"


def render_http_metrics(metrics: HttpMetrics, *, prefix: str) -> str:
    requests, duration_count, duration_sum = metrics.snapshot()
    lines: list[str] = []
    for (method, route, status), count in sorted(requests.items()):
        metric_labels = _metric_labels(method=method, route=route, status=str(status))
        lines.append(f"{prefix}_http_requests_total{metric_labels} {count}")
    for method, route in sorted(duration_count):
        metric_labels = _metric_labels(method=method, route=route)
        lines.append(
            f"{prefix}_http_request_duration_ms_count{metric_labels} "
            f"{duration_count[(method, route)]}"
        )
        lines.append(
            f"{prefix}_http_request_duration_ms_sum{metric_labels} "
            f"{round(duration_sum[(method, route)], 3)}"
        )
    return "\n".join(lines) + ("\n" if lines else "")


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) and path else "<unmatched>"


def configure_http_observability(
    app: FastAPI,
    *,
    metrics: HttpMetrics,
    emit: EventEmitter,
) -> None:
    @app.middleware("http")
    async def observe_request(request: Request, call_next):
        request_id = safe_identifier(request.headers.get("x-request-id")) or uuid4().hex
        trace_id = safe_identifier(request.headers.get("x-trace-id")) or request_id
        started = perf_counter()
        with observation_context(request_id=request_id, trace_id=trace_id):
            try:
                response = await call_next(request)
            except Exception:
                duration_ms = max(0, round((perf_counter() - started) * 1000))
                route = _route_template(request)
                metrics.observe(method=request.method, route=route, status=500, duration_ms=duration_ms)
                emit(
                    "request_failed",
                    method=request.method,
                    route=route,
                    http_status=500,
                    duration_ms=duration_ms,
                )
                raise

            duration_ms = max(0, round((perf_counter() - started) * 1000))
            route = _route_template(request)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Trace-ID"] = trace_id
            metrics.observe(
                method=request.method,
                route=route,
                status=response.status_code,
                duration_ms=duration_ms,
            )
            emit(
                "request_completed",
                method=request.method,
                route=route,
                http_status=response.status_code,
                duration_ms=duration_ms,
            )
            return response


__all__ = ["HttpMetrics", "configure_http_observability", "render_http_metrics"]
