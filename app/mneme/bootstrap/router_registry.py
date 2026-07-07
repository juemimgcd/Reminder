from importlib import import_module

from fastapi import FastAPI


ROUTER_MODULE_NAMES = [
    "app.mneme.routers.health",
    "app.mneme.routers.auth",
    "app.mneme.routers.users",
    "app.mneme.domains.documents.router",
    "app.mneme.domains.retrieval.router",
    "app.mneme.domains.memory.router",
    "app.mneme.domains.advice.router",
    "app.mneme.routers.analysis",
    "app.mneme.domains.profile.router",
    "app.mneme.domains.companion.router",
    "app.mneme.routers.tasks",
    "app.mneme.domains.graph.router",
]


def register_routers(app: FastAPI) -> None:
    for module_name in ROUTER_MODULE_NAMES:
        module = import_module(module_name)
        app.include_router(module.router)
