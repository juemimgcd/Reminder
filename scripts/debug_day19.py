import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from app.mneme.bootstrap.app_factory import create_app
from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES


def main() -> None:
    print("Start Day 19 Bootstrap debug script...", flush=True)
    app = create_app()
    route_paths = {route.path for route in app.routes}

    print(f"project_title={app.title}", flush=True)
    print(f"router_module_count={len(ROUTER_MODULE_NAMES)}", flush=True)
    print(f"route_count={len(route_paths)}", flush=True)
    print(f"has_root={'/' in route_paths}", flush=True)
    print(f"has_hello={'/hello/{name}' in route_paths}", flush=True)
    print(f"has_health={'/health' in route_paths}", flush=True)
    print(f"has_tasks={any(path.startswith('/tasks') for path in route_paths)}", flush=True)
    print(f"has_analysis_analytics={any('/analytics' in path for path in route_paths)}", flush=True)
    print(f"has_graph_rag={any(path.endswith('/rag') for path in route_paths)}", flush=True)


if __name__ == "__main__":
    main()
