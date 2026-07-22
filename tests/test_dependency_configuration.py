import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_DOCS = (
    "docs/architecture.md",
    "docs/runtime-contracts.md",
    "docs/current-state.md",
)
REPOSITORY_PATH = re.compile(r"`((?:app|tests)/[^`]+)`")


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def requirement_entries(path: str) -> list[str]:
    entries: list[str] = []
    for raw_line in read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        entries.append(line)
    return entries


def top_level_import_modules(path: str) -> set[str]:
    tree = ast.parse(read_text(path))
    modules: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_canonical_architecture_documents_are_linked_and_reference_existing_paths():
    readme = read_text("README.md")

    for path in CANONICAL_DOCS:
        assert (ROOT / path).is_file(), f"missing canonical document: {path}"
        assert f"[{path}]({path})" in readme, f"README should link {path}"

        for referenced_path in REPOSITORY_PATH.findall(read_text(path)):
            assert (ROOT / referenced_path).exists(), (
                f"{path} references a missing repository path: {referenced_path}"
            )


def test_root_requirements_is_full_stack_aggregate():
    entries = requirement_entries("requirements.txt")

    assert entries == [
        "-r requirements/base.txt",
        "-r requirements/ai.txt",
        "-r requirements/vector.txt",
    ]


def test_dependency_groups_are_disjoint_and_documented():
    groups = [
        "requirements/base.txt",
        "requirements/ai.txt",
        "requirements/vector.txt",
    ]
    seen: dict[str, str] = {}

    for group in groups:
        text = read_text(group)
        assert text.startswith("# "), f"{group} should start with a short purpose comment"
        for entry in requirement_entries(group):
            package = re.split(r"[<>=!~\[]", entry, maxsplit=1)[0].lower()
            assert package not in seen, f"{package} appears in both {seen[package]} and {group}"
            seen[package] = group

    assert "fastapi" in seen
    assert "langchain-openai" in seen
    assert "pymilvus" in seen


def test_test_requirements_avoid_model_runtime_dependencies():
    entries = requirement_entries("requirements/test.txt")
    forbidden = {"torch", "transformers", "sentence-transformers", "langchain-huggingface", "pymilvus"}

    assert "-r base.txt" in entries
    assert "pytest" in {re.split(r"[<>=!~\[]", entry, maxsplit=1)[0] for entry in entries}
    for entry in entries:
        package = re.split(r"[<>=!~\[]", entry, maxsplit=1)[0].lower()
        assert package not in forbidden


def test_heavy_clients_do_not_import_model_packages_at_module_import_time():
    forbidden_imports = {
        "app/mneme/clients/embedding_client.py": "langchain_huggingface",
        "app/mneme/clients/reranker_client.py": "sentence_transformers",
        "app/mneme/clients/vector_store_client.py": "langchain_milvus",
        "app/mneme/clients/llm_client.py": "langchain_openai",
    }

    for path, forbidden_module in forbidden_imports.items():
        assert forbidden_module not in top_level_import_modules(path)


def test_backend_ci_installs_development_requirements_and_runs_quality_checks():
    workflow = read_text(".github/workflows/reminder-deploy.yml")

    assert "python -m pip install -r requirements/dev.txt" in workflow
    assert "python -m ruff check app main.py tests" in workflow
    assert "python -m pytest -q -p no:cacheprovider" in workflow


def test_ci_runs_real_dependency_integration_and_ai_evaluation_gates():
    workflow = read_text(".github/workflows/reminder-deploy.yml")

    assert "integration-check:" in workflow
    assert "python -m alembic upgrade head" in workflow
    assert "tests/integration" in workflow
    assert "app/mneme/memoria/server/eval/cases.jsonl" in workflow
    assert "app/mneme/memoria/server/eval/multi_agent_cases.jsonl" in workflow


def test_dockerfile_copies_grouped_requirements_before_installing_dependencies():
    dockerfile = read_text("docker/Dockerfile")

    grouped_copy = "COPY requirements/ ./requirements/"
    assert grouped_copy in dockerfile
    assert dockerfile.index(grouped_copy) < dockerfile.index("RUN python -m pip install")


def test_migration_container_upgrades_all_alembic_heads():
    migrate_script = read_text("docker/start-migrate.sh")

    assert "exec alembic upgrade heads" in migrate_script


def test_container_shell_scripts_use_unix_line_endings():
    shell_scripts = (ROOT / "docker").glob("*.sh")

    for script in shell_scripts:
        assert b"\r\n" not in script.read_bytes(), f"{script.name} must use LF line endings"


def test_celery_imports_tasks_from_the_application_package():
    celery_source = read_text("app/mneme/infra/celery_app.py")

    assert '"app.mneme.tasks.index_tasks"' in celery_source
    assert '"app.mneme.tasks.outbox_tasks"' in celery_source


def test_linux_image_uses_cpu_only_pytorch_wheel():
    ai_requirements = read_text("requirements/ai.txt")

    assert (
        "torch @ https://download.pytorch.org/whl/cpu/"
        "torch-2.11.0%2Bcpu-cp312-cp312-manylinux_2_28_x86_64.whl"
    ) in ai_requirements


def test_memory_agent_foundation_dependencies_are_in_the_lightweight_group():
    packages = {
        re.split(r"[<>=!~\[]", entry, maxsplit=1)[0].lower()
        for entry in requirement_entries("requirements/base.txt")
    }

    assert {"fastapi", "httpx", "pyjwt", "asyncpg", "alembic", "celery", "pgvector"} <= packages
