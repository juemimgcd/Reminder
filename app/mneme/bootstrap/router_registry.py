from importlib import import_module

from fastapi import FastAPI


ROUTER_MODULE_NAMES = [
    "app.mneme.routers.health",
    "app.mneme.routers.auth",
    "app.mneme.routers.users",
    "app.mneme.domains.documents.router",
    "app.mneme.domains.retrieval.router",
    "app.mneme.routers.memory",
    "app.mneme.routers.advice",
    "app.mneme.routers.analysis",
    "app.mneme.routers.profile",
    "app.mneme.routers.companion",
    "app.mneme.routers.tasks",
    "app.mneme.domains.graph.router",
]


def register_routers(app: FastAPI) -> None:
    for module_name in ROUTER_MODULE_NAMES:
        module = import_module(module_name)
        app.include_router(module.router)
