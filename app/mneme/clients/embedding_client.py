import os
from pathlib import Path
from typing import Any

from app.mneme.conf.config import settings
from app.mneme.conf.logging import app_logger
from app.mneme.infra.object_cache import get_cached_object, set_cached_object

if settings.HF_ENDPOINT:
    os.environ["HF_ENDPOINT"] = settings.HF_ENDPOINT
os.environ["HF_HUB_ETAG_TIMEOUT"] = str(settings.HF_HUB_ETAG_TIMEOUT)
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = str(settings.HF_HUB_DOWNLOAD_TIMEOUT)

WEIGHT_FILE_PATTERNS = (
    "model.safetensors",
    "*.safetensors",
    "pytorch_model.bin",
    "pytorch_model-*.bin",
)


def _has_sentence_transformer_files(model_dir: Path) -> bool:
    if not ((model_dir / "config.json").exists() or (model_dir / "modules.json").exists()):
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
        if _has_sentence_transformer_files(snapshot_dir):
            return snapshot_dir

    snapshot_dirs = [
        path for path in snapshots_dir.iterdir()
        if path.is_dir() and _has_sentence_transformer_files(path)
    ]
    if not snapshot_dirs:
        return None

    return max(snapshot_dirs, key=lambda path: path.stat().st_mtime)


def resolve_embedding_source() -> tuple[str, bool]:
    cache_dir = Path(settings.EMBEDDING_CACHE_DIR)

    if settings.EMBEDDING_MODEL_PATH:
        configured_path = Path(settings.EMBEDDING_MODEL_PATH).expanduser()
        if configured_path.exists():
            if not _has_sentence_transformer_files(configured_path):
                raise FileNotFoundError(
                    f"Configured EMBEDDING_MODEL_PATH is missing model weight files: {configured_path}"
                )
            return str(configured_path.resolve()), True
        raise FileNotFoundError(
            f"Configured EMBEDDING_MODEL_PATH does not exist: {configured_path}"
        )

    configured_model_name = settings.EMBEDDING_MODEL_NAME.strip()
    configured_model_path = Path(configured_model_name).expanduser()
    if configured_model_path.exists():
        if not _has_sentence_transformer_files(configured_model_path):
            raise FileNotFoundError(
                f"Configured EMBEDDING_MODEL_NAME local path is missing model weight files: {configured_model_path}"
            )
        return str(configured_model_path.resolve()), True

    cached_snapshot_dir = _resolve_cached_snapshot_dir(cache_dir, configured_model_name)
    if cached_snapshot_dir:
        return str(cached_snapshot_dir.resolve()), True

    if settings.EMBEDDING_LOCAL_FILES_ONLY:
        raise FileNotFoundError(
            "Embedding model is configured for local-only loading, but no local model was found. "
            "Run the preload script once or set EMBEDDING_MODEL_PATH to a valid local directory."
        )

    return configured_model_name, False


def get_embeddings() -> Any:
    from langchain_huggingface import HuggingFaceEmbeddings

    cached = get_cached_object("embedding_client")
    if isinstance(cached, HuggingFaceEmbeddings):
        return cached

    cache_dir = Path(settings.EMBEDDING_CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)

    model_source, local_files_only = resolve_embedding_source()
    configured_model_path = Path(settings.EMBEDDING_MODEL_NAME.strip()).expanduser()
    can_fallback_to_remote = (
        not settings.EMBEDDING_LOCAL_FILES_ONLY
        and not settings.EMBEDDING_MODEL_PATH
        and not configured_model_path.exists()
        and model_source != settings.EMBEDDING_MODEL_NAME
    )
    model_kwargs = {
        "device": "cpu",
        "local_files_only": local_files_only,
    }
    if settings.HF_TOKEN:
        model_kwargs["token"] = settings.HF_TOKEN

    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=model_source,
            cache_folder=str(cache_dir),
            model_kwargs=model_kwargs,
            encode_kwargs={"normalize_embeddings": True},
        )
    except OSError as exc:
        if not can_fallback_to_remote:
            raise

        app_logger.bind(module="embedding").warning(
            f"local embedding cache is incomplete, fallback to remote repo: {model_source}; error={exc}"
        )
        model_source = settings.EMBEDDING_MODEL_NAME
        local_files_only = False
        model_kwargs["local_files_only"] = False
        embeddings = HuggingFaceEmbeddings(
            model_name=model_source,
            cache_folder=str(cache_dir),
            model_kwargs=model_kwargs,
            encode_kwargs={"normalize_embeddings": True},
        )
    app_logger.bind(module="embedding").info(
        f"embedding model initialized from {'local cache' if local_files_only else 'remote repo'}: {model_source}"
    )
    return set_cached_object("embedding_client", embeddings)



