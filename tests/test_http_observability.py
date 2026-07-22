import re

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.mneme.observability.context import correlation_fields
from app.mneme.observability.http import HttpMetrics, configure_http_observability, render_http_metrics


def _observed_app():
    app = FastAPI()
    metrics = HttpMetrics()
    events: list[tuple[str, dict[str, str | int]]] = []

    def emit(event: str, **fields: str | int) -> None:
        events.append((event, fields))

    configure_http_observability(app, metrics=metrics, emit=emit)

    @app.get("/items/{item_id}")
    async def item(item_id: str):
        return {"item_id": item_id, **correlation_fields()}

    return app, metrics, events


def test_http_observability_propagates_correlation_and_route_metrics():
    app, metrics, events = _observed_app()

    with TestClient(app) as client:
        response = client.get(
            "/items/42",
            headers={"X-Request-ID": "request-42", "X-Trace-ID": "trace-42"},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "request-42"
    assert response.headers["X-Trace-ID"] == "trace-42"
    assert response.json() == {
        "item_id": "42",
        "request_id": "request-42",
        "trace_id": "trace-42",
    }
    rendered = render_http_metrics(metrics, prefix="mneme")
    assert 'mneme_http_requests_total{method="GET",route="/items/{item_id}",status="200"} 1' in rendered
    assert 'mneme_http_request_duration_ms_count{method="GET",route="/items/{item_id}"} 1' in rendered
    assert events[-1][0] == "request_completed"
    assert events[-1][1]["route"] == "/items/{item_id}"


def test_http_observability_replaces_unsafe_identifiers():
    app, _metrics, _events = _observed_app()

    with TestClient(app) as client:
        response = client.get(
            "/items/7",
            headers={"X-Request-ID": "unsafe value", "X-Trace-ID": "<script>"},
        )

    request_id = response.headers["X-Request-ID"]
    trace_id = response.headers["X-Trace-ID"]
    assert re.fullmatch(r"[0-9a-f]{32}", request_id)
    assert trace_id == request_id
    assert response.json()["request_id"] == request_id
    assert response.json()["trace_id"] == trace_id
