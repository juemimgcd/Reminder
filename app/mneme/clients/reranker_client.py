import asyncio
from pathlib import Path
from typing import Any

from app.mneme.conf.config import settings
from app.mneme.conf.logging import app_logger
from app.mneme.infra.object_cache import get_cached_object, set_cached_object

WEIGHT_FILE_PATTERNS = (
    "model.safetensors",
    "*.safetensors",
    "pytorch_model.bin",
    "pytorch_model-*.bin",
)


def _has_model_files(model_dir: Path) -> bool:
    if not (model_dir / "config.json").exists():
        return False

    for pattern in WEIGHT_FILE_PATTERNS:
        if any(model_dir.rglob(pattern)):
            return True
    return False


def _resolve_cached_snapshot_dir(cache_dir: Path, model_name: str) -> Path | None:
    if not model_name or Path(model_name).exists():
        return None

    repo_cache_dir = cache_dir / f"models--{model_name.replace('/', '--')}"
    snapshots_dir = repo_cache_dir / "snapshots"
    if not snapshots_dir.exists():
        return None

    refs_main = repo_cache_dir / "refs" / "main"
    if refs_main.exists():
        revision = refs_main.read_text(encoding="utf-8").strip()
        snapshot_dir = snapshots_dir / revision
        if _has_model_files(snapshot_dir):
            return snapshot_dir

    snapshot_dirs = [path for path in snapshots_dir.iterdir() if path.is_dir() and _has_model_files(path)]
    if not snapshot_dirs:
        return None

    return max(snapshot_dirs, key=lambda path: path.stat().st_mtime)


def resolve_reranker_source() -> tuple[str, bool]:
    cache_dir = Path(settings.RERANKER_CACHE_DIR)

    if settings.RERANKER_MODEL_PATH:
        configured_path = Path(settings.RERANKER_MODEL_PATH).expanduser()
        if configured_path.exists():
            if not _has_model_files(configured_path):
                raise FileNotFoundError(
                    f"Configured RERANKER_MODEL_PATH is missing model weight files: {configured_path}"
                )
            return str(configured_path.resolve()), True
        raise FileNotFoundError(f"Configured RERANKER_MODEL_PATH does not exist: {configured_path}")

    configured_model_name = settings.RERANKER_MODEL_NAME.strip()
    configured_model_path = Path(configured_model_name).expanduser()
    if configured_model_path.exists():
        if not _has_model_files(configured_model_path):
            raise FileNotFoundError(
                f"Configured RERANKER_MODEL_NAME local path is missing model weight files: {configured_model_path}"
            )
        return str(configured_model_path.resolve()), True

    cached_snapshot_dir = _resolve_cached_snapshot_dir(cache_dir, configured_model_name)
    if cached_snapshot_dir:
        return str(cached_snapshot_dir.resolve()), True

    if settings.RERANKER_LOCAL_FILES_ONLY:
        raise FileNotFoundError(
            "Reranker is configured for local-only loading, but no local model was found. "
            "Set RERANKER_MODEL_PATH or preload the reranker model first."
        )

    return configured_model_name, False


def get_reranker() -> Any | None:
    if not settings.RERANKER_ENABLED:
        return None

    from sentence_transformers import CrossEncoder

    cached = get_cached_object("reranker_client")
    if isinstance(cached, CrossEncoder):
        return cached

    cache_dir = Path(settings.RERANKER_CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)

    model_source, local_files_only = resolve_reranker_source()
    configured_model_path = Path(settings.RERANKER_MODEL_NAME.strip()).expanduser()
    can_fallback_to_remote = (
        not settings.RERANKER_LOCAL_FILES_ONLY
        and not settings.RERANKER_MODEL_PATH
        and not configured_model_path.exists()
        and model_source != settings.RERANKER_MODEL_NAME
    )

    try:
        reranker = CrossEncoder(
            model_name=model_source,
            cache_folder=str(cache_dir),
            local_files_only=local_files_only,
            trust_remote_code=True,
        )
    except OSError as exc:
        if not can_fallback_to_remote:
            raise

        app_logger.bind(module="reranker").warning(
            f"local reranker cache is incomplete, fallback to remote repo: {model_source}; error={exc}"
        )
        reranker = CrossEncoder(
            model_name=settings.RERANKER_MODEL_NAME,
            cache_folder=str(cache_dir),
            local_files_only=False,
            trust_remote_code=True,
        )
        model_source = settings.RERANKER_MODEL_NAME
        local_files_only = False

    app_logger.bind(module="reranker").info(
        f"reranker initialized from {'local cache' if local_files_only else 'remote repo'}: {model_source}"
    )
    return set_cached_object("reranker_client", reranker)


async def rerank_pairs(*, pairs: list[tuple[str, str]]) -> list[float]:
    reranker = get_reranker()
    if reranker is None or not pairs:
        return []

    scores = await asyncio.to_thread(reranker.predict, pairs)
    return [float(score) for score in scores]
