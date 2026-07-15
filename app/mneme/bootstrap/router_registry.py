from importlib import import_module

from fastapi import FastAPI

ROUTER_MODULE_NAMES = [
    "app.mneme.domains.health.router",
    "app.mneme.domains.auth.router",
    "app.mneme.domains.users.router",
    "app.mneme.domains.settings.router",
    "app.mneme.domains.documents.router",
    "app.mneme.domains.documents.folders",
    "app.mneme.domains.chat.router",
    "app.mneme.domains.chat.run_router",
    "app.mneme.domains.retrieval.router",
    "app.mneme.domains.memory.router",
    "app.mneme.domains.advice.router",
    "app.mneme.domains.analysis.router",
    "app.mneme.domains.profile.router",
    "app.mneme.domains.companion.router",
    "app.mneme.domains.tasks.router",
    "app.mneme.domains.graph.router",
    "app.mneme.domains.support.router",
]


def register_routers(app: FastAPI) -> None:
    for module_name in ROUTER_MODULE_NAMES:
        module = import_module(module_name)
        app.include_router(module.router)
