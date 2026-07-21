from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.mneme.conf.agent_config import load_memoria_config, mneme_agent_settings
from app.mneme.version import __version__

DEFAULT_BASE_DIR = Path(__file__).resolve().parents[3]

DEFAULT_CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=DEFAULT_BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    BASE_DIR: Path = DEFAULT_BASE_DIR
    APP_ENV: Literal["development", "test", "production"] = "development"

    PROJECT_NAME: str = "Mneme"
    VERSION: str = __version__
    DESCRIPTION: str = "A private memory-oriented RAG knowledge assistant"
    LOG_LEVEL: str = "INFO"

    API_PREFIX: str = "/api/v1"
    CORS_ALLOWED_ORIGINS: list[str] = Field(
        default_factory=lambda: list(DEFAULT_CORS_ALLOWED_ORIGINS),
    )
    CORS_ALLOW_ORIGIN_REGEX: str = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_HEADERS: list[str] = Field(default_factory=lambda: ["*"])
    TRUSTED_HOSTS: list[str] = Field(default_factory=list)

    DATABASE_URL: str = "postgresql+asyncpg://postgres:123456@localhost:5432/agentic"

    STORAGE_DIR: Path = DEFAULT_BASE_DIR / "storage"
    RAW_FILE_DIR: Path = DEFAULT_BASE_DIR / "storage" / "raw"

    # ALLOWED_EXTENSIONS includes common document, spreadsheet, data, and web formats.
    ALLOWED_EXTENSIONS: set[str] = {
        ".pdf",
        ".txt",
        ".md",
        ".docx",
        ".pptx",
        ".xlsx",
        ".xls",
        ".csv",
        ".json",
        ".xml",
        ".html",
        ".htm",
        ".epub",
    }
    MAX_FILE_SIZE: int = 10 * 1024 * 1024

    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    EMBEDDING_MODEL_PATH: str = ""
    EMBEDDING_CACHE_DIR: Path = DEFAULT_BASE_DIR / "storage" / "model_cache" / "sentence_transformers"
    EMBEDDING_LOCAL_FILES_ONLY: bool = False
    EMBEDDING_PRELOAD_ON_STARTUP: bool = False
    RERANKER_ENABLED: bool = False
    RERANKER_MODEL_NAME: str = "BAAI/bge-reranker-v2-m3"
    RERANKER_MODEL_PATH: str = ""
    RERANKER_CACHE_DIR: Path = DEFAULT_BASE_DIR / "storage" / "model_cache" / "reranker"
    RERANKER_LOCAL_FILES_ONLY: bool = False
    RERANKER_PRELOAD_ON_STARTUP: bool = False
    HF_ENDPOINT: str = ""
    HF_HUB_ETAG_TIMEOUT: int = 10
    HF_HUB_DOWNLOAD_TIMEOUT: int = 10
    HF_TOKEN: str = ""
    VECTOR_BACKEND: str = "milvus"
    GRAPH_BACKEND: str = "neo4j"
    MILVUS_URI: str = "http://127.0.0.1:19530"
    MILVUS_TOKEN: str = ""
    MILVUS_DB_NAME: str = "default"
    MILVUS_COLLECTION_NAME: str = "document_chunks"
    MILVUS_INDEX_TYPE: str = "FLAT"
    MILVUS_METRIC_TYPE: str = "IP"
    MILVUS_SEARCH_PARAMS: str = '{"metric_type":"IP"}'
    MILVUS_CONSISTENCY_LEVEL: str = "Strong"
    MILVUS_DROP_OLD: bool = False
    NEO4J_ENABLED: bool = True
    NEO4J_URI: str = "bolt://127.0.0.1:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "change-this-in-production"
    NEO4J_DATABASE: str = "neo4j"
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = 20

    MEMORY_AGENT_BASE_URL: str = "http://127.0.0.1:8010"
    MEMORY_AGENT_SERVICE_JWT_SECRET: SecretStr = SecretStr("")
    MEMORY_AGENT_TIMEOUT_SECONDS: int = 30
    MEMORY_AGENT_OUTBOX_TARGET: str = "memory_agent_http"

    LLM_PROVIDER: str = "deepseek"
    LLM_API_KEY: str = ""
    DASHSCOPE_API_KEY: str = ""
    MIMO_API_KEY: str = ""
    KIMI_API_KEY: str = ""
    GLM_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL_NAME: str = ""
    LLM_TEMPERATURE: float = 0.0
    LLM_CONTEXT_WINDOW: int = 64000

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
    CELERY_OUTBOX_QUEUE: str = "outbox_projection"
    CELERY_AGENT_QUEUE: str = "agent_run"
    CELERY_AUTOMATION_QUEUE: str = "agent_automation"
    CELERY_MAINTENANCE_QUEUE: str = "maintenance"
    CELERY_CHANNEL_QUEUE: str = "channel_delivery"
    MAINTENANCE_PENDING_RECOVERY_SECONDS: int = 30
    MAINTENANCE_TASK_STALE_SECONDS: int = 1800
    MAINTENANCE_RECOVERY_BATCH_SIZE: int = 20
    CELERY_TASK_MAX_RETRIES: int = 3
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1

    RETRIEVAL_VECTOR_RECALL_K: int = 12
    RETRIEVAL_KEYWORD_RECALL_K: int = 12
    RETRIEVAL_MEMORY_RECALL_K: int = 8
    RETRIEVAL_RERANK_CANDIDATE_K: int = 20
    RETRIEVAL_CONTEXT_BUDGET_CHARS: int = 4000

    INDEX_VECTOR_BATCH_SIZE: int = 64
    OUTBOX_EVENT_MAX_ATTEMPTS: int = 5
    OUTBOX_RETRY_BASE_DELAY_SECONDS: int = 30

    FEISHU_ENABLED: bool = False
    FEISHU_ACCOUNT_ID: str = "default"
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: SecretStr = SecretStr("")
    FEISHU_VERIFICATION_TOKEN: SecretStr = SecretStr("")
    FEISHU_API_BASE_URL: str = "https://open.feishu.cn"
    FEISHU_MAX_TEXT_CHARS: int = 3500
    CHANNEL_LINK_CODE_TTL_SECONDS: int = 600
    CHANNEL_DELIVERY_MAX_ATTEMPTS: int = 5
    CHANNEL_DELIVERY_RETRY_BASE_SECONDS: int = 15
    CHANNEL_DELIVERY_DISPATCH_BATCH_SIZE: int = 20
    CHANNEL_DELIVERY_STALE_SECONDS: int = 300

    RATE_LIMIT_WINDOW_SECONDS: int = 60
    UPLOAD_RATE_LIMIT_MAX: int = 10
    INDEX_SUBMIT_RATE_LIMIT_MAX: int = 20
    CHAT_QUERY_RATE_LIMIT_MAX: int = 30

    AGENT_HISTORY_MAX_TURNS: int = 12
    AGENT_OUTPUT_RESERVE_TOKENS: int = 4096
    AGENT_SUMMARY_MAX_CHARS: int = 2000
    AGENT_CHARS_PER_TOKEN: float = 3.0
    AGENT_RUN_REDIS_URL: str = "redis://localhost:6379/4"
    AGENT_RUN_ALLOW_MEMORY_FALLBACK: bool = True
    AGENT_RUN_TTL_SECONDS: int = 3600
    AGENT_RUN_EVENT_MAXLEN: int = 1000
    AGENT_RUN_POLL_INTERVAL_SECONDS: float = 0.2
    AGENT_SESSION_LEASE_SECONDS: int = 120
    AGENT_SESSION_LEASE_RENEW_SECONDS: float = 30.0
    AGENT_TOOL_RESULT_SOFT_CHARS: int = 600
    AGENT_RUNTIME_AUDIT_ENABLED: bool = True
    AGENT_RUNTIME_METRICS_MAX_TRACES: int = 1000
    AGENT_RUN_STALE_SECONDS: int = 180
    AGENT_RUN_RECOVERY_BATCH_SIZE: int = 50
    AGENT_RUN_MAX_ATTEMPTS: int = 3
    HEARTBEAT_DISPATCH_INTERVAL_SECONDS: int = 30
    HEARTBEAT_DISPATCH_BATCH_SIZE: int = 20

    EXTERNAL_RETRY_MAX_ATTEMPTS: int = 3
    EXTERNAL_RETRY_BASE_DELAY_SECONDS: float = 0.5
    EXTERNAL_RETRY_MAX_DELAY_SECONDS: float = 4.0

    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 3
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS: int = 30

    @model_validator(mode="after")
    def validate_environment(self) -> "Settings":
        if self.APP_ENV != "production":
            merged = [*self.CORS_ALLOWED_ORIGINS]
            for origin in DEFAULT_CORS_ALLOWED_ORIGINS:
                if origin not in merged:
                    merged.append(origin)
            self.CORS_ALLOWED_ORIGINS = merged
            return self

        if "CORS_ALLOWED_ORIGINS" not in self.model_fields_set:
            self.CORS_ALLOWED_ORIGINS = []
        if "CORS_ALLOW_ORIGIN_REGEX" not in self.model_fields_set:
            self.CORS_ALLOW_ORIGIN_REGEX = ""

        jwt_secret = self.JWT_SECRET.strip()
        service_secret = self.MEMORY_AGENT_SERVICE_JWT_SECRET.get_secret_value().strip()
        errors: list[str] = []
        if len(jwt_secret) < 32 or "change-this" in jwt_secret or "replace-with" in jwt_secret:
            errors.append("JWT_SECRET must be a non-placeholder value of at least 32 characters")
        if len(service_secret) < 32 or "change-this" in service_secret or "replace-with" in service_secret:
            errors.append("MEMORY_AGENT_SERVICE_JWT_SECRET must be a non-placeholder value of at least 32 characters")
        if jwt_secret and jwt_secret == service_secret:
            errors.append("JWT_SECRET and MEMORY_AGENT_SERVICE_JWT_SECRET must be different")
        if ":123456@" in self.DATABASE_URL:
            errors.append("DATABASE_URL must not use the default PostgreSQL password")
        if self.NEO4J_ENABLED and self.NEO4J_PASSWORD == "change-this-in-production":
            errors.append("NEO4J_PASSWORD must not use the production placeholder")
        if errors:
            raise ValueError("unsafe production configuration: " + "; ".join(errors))
        return self




settings = Settings(**mneme_agent_settings(load_memoria_config()))
