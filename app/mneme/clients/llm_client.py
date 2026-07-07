from langchain_openai import ChatOpenAI

from app.mneme.conf.config import settings

QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL_NAME = "qwen-plus"

LLM_PROVIDER_DEFAULTS = {
    "qwen": {
        "base_url": QWEN_BASE_URL,
        "model": QWEN_MODEL_NAME,
        "api_key_field": "DASHSCOPE_API_KEY",
    },
    "mimo": {
        "base_url": "https://api.xiaomimimo.com/v1",
        "model": "mimo-v2.5-pro",
        "api_key_field": "MIMO_API_KEY",
    },
    "kimi": {
        "base_url": "https://api.moonshot.ai/v1",
        "model": "kimi-k2.6",
        "api_key_field": "KIMI_API_KEY",
    },
    "glm": {
        "base_url": "https://api.z.ai/api/paas/v4",
        "model": "glm-5",
        "api_key_field": "GLM_API_KEY",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
        "api_key_field": "DEEPSEEK_API_KEY",
    },
}


def _normalize_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized in LLM_PROVIDER_DEFAULTS:
        return normalized
    return "qwen"


def build_llm_kwargs(config=settings) -> dict:
    provider = _normalize_provider(config.LLM_PROVIDER)
    defaults = LLM_PROVIDER_DEFAULTS[provider]

    base_url = config.LLM_BASE_URL.strip()
    if not base_url or (provider != "qwen" and base_url == QWEN_BASE_URL):
        base_url = defaults["base_url"]

    model_name = config.LLM_MODEL_NAME.strip()
    if not model_name or (provider != "qwen" and model_name == QWEN_MODEL_NAME):
        model_name = defaults["model"]

    api_key = config.LLM_API_KEY.strip() or getattr(config, defaults["api_key_field"]).strip()
    kwargs = {
        "model": model_name,
        "api_key": api_key,
        "base_url": base_url,
        "temperature": config.LLM_TEMPERATURE,
    }

    if provider == "mimo" and api_key:
        kwargs["default_headers"] = {"api-key": api_key}

    return kwargs


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(**build_llm_kwargs(settings))
