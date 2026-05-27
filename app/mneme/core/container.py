from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES
from app.mneme.conf.config import settings


def build_runtime_container() -> dict:
    return {
        "settings": settings,
        "router_module_names": ROUTER_MODULE_NAMES,
    }


__all__ = ["build_runtime_container"]
