import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def imported_modules(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def violations(root, forbidden):
    found = []
    for path in root.rglob("*.py"):
        for module in imported_modules(path):
            if any(module == prefix or module.startswith(f"{prefix}.") for prefix in forbidden):
                found.append(f"{path.relative_to(ROOT)}: {module}")
    return found


def test_memory_agent_does_not_import_mneme_persistence_or_tasks():
    forbidden = ("app.mneme.models", "app.mneme.crud", "app.mneme.conf.database", "app.mneme.tasks")
    assert violations(ROOT / "services" / "memory_agent", forbidden) == []


def test_mneme_does_not_import_memory_agent_persistence_or_tasks():
    forbidden = (
        "services.memory_agent.models",
        "services.memory_agent.repositories",
        "services.memory_agent.database",
        "services.memory_agent.tasks",
    )
    assert violations(ROOT / "app" / "mneme", forbidden) == []

