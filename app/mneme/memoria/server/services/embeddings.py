import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.mneme.memoria.server.config import settings


@lru_cache(maxsize=1)
def _embedding_model() -> Any:
    from sentence_transformers import SentenceTransformer

    cache_dir = Path(settings.EMBEDDING_CACHE_DIR).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_source = settings.EMBEDDING_MODEL_PATH.strip() or settings.EMBEDDING_MODEL_NAME.strip()
    if not model_source:
        raise RuntimeError("embedding model path or name must be configured")
    return SentenceTransformer(
        model_source,
        cache_folder=str(cache_dir),
        local_files_only=settings.EMBEDDING_LOCAL_FILES_ONLY,
    )


def embedding_model_ready() -> bool:
    return _embedding_model.cache_info().currsize > 0


def preload_embedding_model_sync() -> None:
    _embedding_model()


async def preload_embedding_model() -> None:
    await asyncio.to_thread(preload_embedding_model_sync)


def _embed_texts_sync(texts: list[str]) -> list[list[float]]:
    vectors = _embedding_model().encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    result = vectors.tolist()
    if len(result) != len(texts):
        raise RuntimeError("embedding model returned an unexpected vector count")
    if any(len(vector) != settings.EMBEDDING_DIMENSION for vector in result):
        raise RuntimeError(
            f"embedding model must return {settings.EMBEDDING_DIMENSION}-dimension vectors"
        )
    return result


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return await asyncio.to_thread(_embed_texts_sync, texts)
