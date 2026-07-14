from pydantic import SecretStr
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


settings = MemoryAgentSettings()
