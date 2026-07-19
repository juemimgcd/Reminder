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
    ANSWER_LLM_CONTEXT_WINDOW: int = Field(default=64000, ge=1000, le=1000000)
    ANSWER_LLM_MAX_ATTEMPTS: int = Field(default=3, ge=1, le=5)
    ANSWER_LLM_RETRY_BASE_SECONDS: float = Field(default=0.5, ge=0, le=30)
    ANSWER_LLM_RETRY_MAX_SECONDS: float = Field(default=4.0, ge=0, le=60)
    ANSWER_LLM_FALLBACK_PROVIDER: str = ""
    ANSWER_LLM_FALLBACK_BASE_URL: str = ""
    ANSWER_LLM_FALLBACK_API_KEY: SecretStr = SecretStr("")
    ANSWER_LLM_FALLBACK_MODEL: str = ""
    ANSWER_LLM_FALLBACK_TEMPERATURE: float = 0.0
    ANSWER_LLM_FALLBACK_CONTEXT_WINDOW: int = Field(default=64000, ge=1000, le=1000000)
    ANSWER_MAX_CONTEXT_CHARS: int = Field(default=24000, ge=1000, le=100000)
    ANSWER_CONTEXT_CHARS_PER_TOKEN: float = Field(default=3.0, ge=1, le=8)
    ANSWER_PROMPT_RESERVE_TOKENS: int = Field(default=1024, ge=256, le=16000)
    ANSWER_MAX_QUESTION_CHARS: int = Field(default=8000, ge=100, le=20000)
    ANSWER_MAX_OUTPUT_TOKENS: int = Field(default=1200, ge=100, le=8000)
    ANSWER_REASONING_MAX_STEPS: int = Field(default=3, ge=1, le=5)
    ANSWER_REASONING_SUMMARY_MAX_CHARS: int = Field(default=600, ge=100, le=2000)
    ANSWER_REASONING_TOTAL_OUTPUT_TOKENS: int = Field(default=3600, ge=100, le=16000)
    ANSWER_TOOL_MAX_CALLS: int = Field(default=4, ge=0, le=12)
    ANSWER_TOOL_OBSERVATION_MAX_CHARS: int = Field(default=2000, ge=200, le=8000)
    ANSWER_RUN_STALE_SECONDS: int = Field(default=180, ge=30, le=86400)
    ANSWER_RUN_RECOVERY_BATCH_SIZE: int = Field(default=100, ge=1, le=1000)
    MULTI_AGENT_FEATURE_ENABLED: bool = True
    MULTI_AGENT_ROLLOUT_PERCENT: int = Field(default=100, ge=0, le=100)
    MULTI_AGENT_ALLOWED_MODES: str = "analysis_query"
    MULTI_AGENT_DEADLINE_SECONDS: float = Field(default=20, gt=0, le=120)
    MULTI_AGENT_SOURCE_TIMEOUT_SECONDS: float = Field(default=8, gt=0, le=60)
    MULTI_AGENT_MAX_MODEL_CALLS: int = Field(default=4, ge=1, le=16)
    MULTI_AGENT_MAX_PROMPT_TOKENS: int = Field(default=12000, ge=512, le=200000)
    MULTI_AGENT_MAX_COMPLETION_TOKENS: int = Field(default=3600, ge=128, le=32000)
    MULTI_AGENT_MAX_RETRIEVAL_TOP_K: int = Field(default=24, ge=1, le=40)
    MULTI_AGENT_MAX_ESTIMATED_COST: float = Field(default=1.0, ge=0, le=100)


settings = MemoryAgentSettings()
