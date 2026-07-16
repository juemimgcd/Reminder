import asyncio
from functools import lru_cache
from typing import Any

from app.mneme.memoria.server.config import settings


@lru_cache(maxsize=1)
def _embedding_model() -> Any:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.EMBEDDING_MODEL_NAME)


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
