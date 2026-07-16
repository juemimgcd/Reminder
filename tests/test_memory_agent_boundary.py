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


def violations(root, forbidden, *, excluded_roots=()):
    found = []
    for path in root.rglob("*.py"):
        if any(path.is_relative_to(excluded_root) for excluded_root in excluded_roots):
            continue
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
    assert violations(ROOT / "app" / "mneme" / "memoria" / "server", forbidden) == []


def test_mneme_does_not_import_memory_agent_persistence_or_tasks():
    forbidden = (
        "app.mneme.memoria.server.models",
        "app.mneme.memoria.server.repositories",
        "app.mneme.memoria.server.database",
        "app.mneme.memoria.server.tasks",
    )
    assert violations(
        ROOT / "app" / "mneme",
        forbidden,
        excluded_roots=(ROOT / "app" / "mneme" / "memoria" / "server",),
    ) == []


def test_import_from_scanner_covers_direct_and_similar_names():
    sample = ROOT / ".boundary-scanner-sample.py"
    sample.write_text(
        "from app.mneme import models\n"
        "from app.mneme.memoria.server import database\n"
        "from app.mneme.memoria.server import models_extra\n"
        "from app.mneme.memoria.server.models import InboxEvent\n",
        encoding="utf-8",
    )
    try:
        modules = set(imported_modules(sample))

        assert "app.mneme.models" in modules
        assert "app.mneme.memoria.server.database" in modules
        assert "app.mneme.memoria.server.models.InboxEvent" in modules
        assert "app.mneme.memoria.server.models_extra" in modules
        assert not any(module == "app.mneme.memoria.server.models" for module in modules)
    finally:
        sample.unlink(missing_ok=True)


def test_import_from_scanner_detects_forbidden_parent_import():
    fixture_dir = ROOT / ".boundary-scanner-fixture"
    fixture_dir.mkdir(exist_ok=True)
    sample = fixture_dir / "sample.py"
    sample.write_text("from app.mneme.memoria.server import database\n", encoding="utf-8")
    try:
        found = violations(fixture_dir, ("app.mneme.memoria.server.database",))
        assert [item.replace("\\", "/") for item in found] == [
            ".boundary-scanner-fixture/sample.py: app.mneme.memoria.server.database"
        ]
    finally:
        sample.unlink(missing_ok=True)
        fixture_dir.rmdir()
