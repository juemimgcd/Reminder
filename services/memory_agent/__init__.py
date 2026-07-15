"""Mneme Memory Agent service."""


def create_memory_agent_app(*args, **kwargs):
    """Build the ASGI application without importing the runtime at package import time.

    Keeping this import lazy lets the standard-library evaluation CLI run in a
    lightweight CI environment that does not install the API server extras.
    """

    from services.memory_agent.app import create_memory_agent_app as _create_app

    return _create_app(*args, **kwargs)

__all__ = ["create_memory_agent_app"]
