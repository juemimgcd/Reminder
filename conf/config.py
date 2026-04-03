import os
from pathlib import Path


class Settings:
    # `__file__` 是当前这个文件自己的路径。
    # `parent.parent` 往上退两层，就能拿到项目根目录。
    BASE_DIR = Path(__file__).resolve().parent.parent

    PROJECT_NAME = "Agentic RAG Assistant"
    VERSION = "0.1.0"
    DESCRIPTION = "一个基于 FastAPI 的 Agentic RAG 私有知识助手后端项目"

    API_PREFIX = "/api/v1"

    # Alembic 和应用本身都统一从这里拿数据库地址，避免两边各写各的。
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:123456@localhost:5432/agentic",
    )

    # 先把存储目录约定好，后面 Day 3 上传文件时直接复用。
    STORAGE_DIR = BASE_DIR / "storage"
    RAW_FILE_DIR = STORAGE_DIR / "raw"

    # 这里先把允许的上传类型和大小写死，后面再改成环境变量也不迟。
    ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
    MAX_FILE_SIZE = 10 * 1024 * 1024


settings = Settings()
