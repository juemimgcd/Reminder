from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # 本地开发统一从项目根目录 .env 读取；
        # 容器环境下则优先读取注入进进程的环境变量。
        env_file=DEFAULT_BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    BASE_DIR: Path = DEFAULT_BASE_DIR

    PROJECT_NAME: str = "Agentic RAG Assistant"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "一个基于 FastAPI 的 Agentic RAG 私有知识助手后端项目"

    API_PREFIX: str = "/api/v1"

    # 数据库地址默认给出本地开发值，同时允许通过 .env 完整覆盖。
    DATABASE_URL: str = "postgresql+asyncpg://postgres:123456@localhost:5432/agentic"

    # 这几个路径字段都可以在 .env 里单独改；如果不配，就用项目默认目录。
    STORAGE_DIR: Path = DEFAULT_BASE_DIR / "storage"
    RAW_FILE_DIR: Path = DEFAULT_BASE_DIR / "storage" / "raw"

    # 如果你要在 .env 里覆盖 set/list 这类复杂类型，推荐写成 JSON：
    # ALLOWED_EXTENSIONS=[".pdf",".txt",".md"]
    ALLOWED_EXTENSIONS: set[str] = {".pdf", ".txt", ".md"}
    MAX_FILE_SIZE: int = 10 * 1024 * 1024

    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-mpnet-base-v2"
    VECTOR_BACKEND: str = "milvus"
    MILVUS_URI: str = str(DEFAULT_BASE_DIR / "storage" / "milvus.db")
    MILVUS_TOKEN: str = ""
    MILVUS_DB_NAME: str = "default"
    MILVUS_COLLECTION_NAME: str = "document_chunks"
    MILVUS_INDEX_TYPE: str = "FLAT"
    MILVUS_METRIC_TYPE: str = "IP"
    MILVUS_SEARCH_PARAMS: str = '{"metric_type":"IP"}'
    MILVUS_CONSISTENCY_LEVEL: str = "Strong"
    MILVUS_DROP_OLD: bool = False

    DASHSCOPE_API_KEY: str = ""
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_MODEL_NAME: str = "qwen-plus"
    LLM_TEMPERATURE: float = 0.0

    JWT_SECRET: str = Field(
        default="dev-only-change-this-secret-key",
        validation_alias=AliasChoices("JWT_SECRET", "JWT_SECRET_KEY"),
    )
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        validation_alias=AliasChoices("ACCESS_TOKEN_EXPIRE_MINUTES", "JWT_ACCESS_TOKEN_EXPIRE_MINUTES"),
    )

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    CELERY_INDEX_QUEUE: str = "document_index"


settings = Settings()
