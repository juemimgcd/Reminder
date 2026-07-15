import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def imported_modules(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if alias.name == "*":
                    yield node.module
                else:
                    yield f"{node.module}.{alias.name}"


def violations(root, forbidden):
    found = []
    for path in root.rglob("*.py"):
        for module in imported_modules(path):
            if any(module == prefix or module.startswith(f"{prefix}.") for prefix in forbidden):
                try:
                    display_path = path.relative_to(ROOT)
                except ValueError:
                    display_path = path.name
                found.append(f"{display_path}: {module}")
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


def test_import_from_scanner_covers_direct_and_similar_names():
    sample = ROOT / ".boundary-scanner-sample.py"
    sample.write_text(
        "from app.mneme import models\n"
        "from services.memory_agent import database\n"
        "from services.memory_agent import models_extra\n"
        "from services.memory_agent.models import InboxEvent\n",
        encoding="utf-8",
    )
    try:
        modules = set(imported_modules(sample))

        assert "app.mneme.models" in modules
        assert "services.memory_agent.database" in modules
        assert "services.memory_agent.models.InboxEvent" in modules
        assert "services.memory_agent.models_extra" in modules
        assert not any(module == "services.memory_agent.models" for module in modules)
    finally:
        sample.unlink(missing_ok=True)


def test_import_from_scanner_detects_forbidden_parent_import():
    fixture_dir = ROOT / ".boundary-scanner-fixture"
    fixture_dir.mkdir(exist_ok=True)
    sample = fixture_dir / "sample.py"
    sample.write_text("from services.memory_agent import database\n", encoding="utf-8")
    try:
        assert violations(fixture_dir, ("services.memory_agent.database",)) == [
            ".boundary-scanner-fixture\\sample.py: services.memory_agent.database"
        ]
    finally:
        sample.unlink(missing_ok=True)
        fixture_dir.rmdir()
