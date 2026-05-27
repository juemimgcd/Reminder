import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.mneme.bootstrap.app_factory import create_app  # noqa: E402
from main import app as legacy_app  # noqa: E402


REQUIRED_PATHS = [
    "app/mneme/main.py",
    "app/mneme/bootstrap/app_factory.py",
    "app/mneme/bootstrap/router_registry.py",
    "app/mneme/api/router.py",
    "app/mneme/api/deps.py",
    "app/mneme/api/response.py",
    "app/mneme/api/errors.py",
    "app/mneme/core/config.py",
    "app/mneme/core/container.py",
    "app/mneme/core/logging.py",
    "app/mneme/domains/documents",
    "app/mneme/domains/retrieval",
    "app/mneme/domains/eval",
    "app/mneme/domains/memory",
    "app/mneme/domains/graph",
    "app/mneme/domains/profile",
    "app/mneme/domains/tasks",
    "app/mneme/workflow/jobs",
    "app/mneme/workflow/dispatcher.py",
    "app/mneme/workflow/task_state.py",
    "app/mneme/workflow/outbox.py",
    "app/mneme/workflow/queue.py",
    "app/mneme/infra/vector_store",
    "app/mneme/infra/relational_store/postgresql.py",
    "app/mneme/infra/graph_store/neo4j.py",
    "app/mneme/infra/cache/redis.py",
    "app/mneme/infra/message_queue/rabbitmq.py",
    "app/mneme/infra/retry",
    "app/mneme/infra/rate_limit",
]


def main() -> None:
    missing_paths = [
        path
        for path in REQUIRED_PATHS
        if not (PROJECT_ROOT / path).exists()
    ]
    if missing_paths:
        raise AssertionError(f"missing layered paths: {missing_paths}")

    app = create_app()
    route_paths = {route.path for route in app.routes}

    required_routes = {
        "/",
        "/health",
        "/health/readiness",
        "/kb/documents/upload",
        "/graph/knowledge-bases/{knowledge_base_id}/rag",
    }
    missing_routes = sorted(required_routes - route_paths)
    if missing_routes:
        raise AssertionError(f"missing routes: {missing_routes}")

    assert legacy_app.title == app.title
    print(f"layered_structure_ok=True paths={len(REQUIRED_PATHS)} routes={len(route_paths)}")


if __name__ == "__main__":
    main()
