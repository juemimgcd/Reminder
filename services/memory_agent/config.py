from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class MemoryAgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MEMORY_AGENT_",
        env_file=".env",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+asyncpg://postgres:123456@localhost:5432/memory_agent"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8010
    SERVICE_JWT_SECRET: SecretStr
    SERVICE_JWT_AUDIENCE: str = "memory-agent"
    CELERY_BROKER_URL: str = "redis://localhost:6379/2"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/3"
    CELERY_QUEUE: str = "memory_agent"
    EMBEDDING_DIMENSION: int = 1024
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    EXTRACTION_LLM_BASE_URL: str = ""
    EXTRACTION_LLM_API_KEY: SecretStr = SecretStr("")
    EXTRACTION_LLM_MODEL: str = ""
    EXTRACTION_LLM_TEMPERATURE: float = 0.0
    ANSWER_LLM_PROVIDER: str = "openai"
    ANSWER_LLM_BASE_URL: str = ""
    ANSWER_LLM_API_KEY: SecretStr = SecretStr("")
    ANSWER_LLM_MODEL: str = ""
    ANSWER_LLM_TEMPERATURE: float = 0.0
    ANSWER_MAX_CONTEXT_CHARS: int = Field(default=24000, ge=1000, le=100000)
    ANSWER_MAX_QUESTION_CHARS: int = Field(default=8000, ge=100, le=20000)
    ANSWER_MAX_OUTPUT_TOKENS: int = Field(default=1200, ge=100, le=8000)


settings = MemoryAgentSettings()
