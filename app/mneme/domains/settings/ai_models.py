import base64
import hashlib
import uuid

from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.clients.llm_client import LLM_PROVIDER_DEFAULTS
from app.mneme.conf.config import settings
from app.mneme.crud.ai_model_config import (
    clear_default_ai_model_configs,
    create_ai_model_config as insert_ai_model_config,
    get_ai_model_config,
    list_ai_model_configs,
)
from app.mneme.models.ai_model_config import AiModelConfig
from app.mneme.models.user import User
from app.mneme.schemas.ai_model_config import (
    AiModelConfigCreateRequest,
    AiModelConfigUpdateRequest,
    AiModelProviderPreset,
)
from app.mneme.utils.exceptions import BusinessException


def build_ai_model_config_id() -> str:
    return f"model_{uuid.uuid4().hex[:16]}"


def provider_presets() -> list[AiModelProviderPreset]:
    labels = {
        "qwen": "Qwen",
        "mimo": "MiMo",
        "kimi": "Kimi",
        "glm": "GLM",
        "deepseek": "DeepSeek",
    }
    return [
        AiModelProviderPreset(
            provider=provider,
            label=labels.get(provider, provider.title()),
            base_url=str(defaults["base_url"]),
            model_name=str(defaults["model"]),
        )
        for provider, defaults in LLM_PROVIDER_DEFAULTS.items()
    ]


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.JWT_SECRET.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    return _fernet().encrypt(api_key.encode("utf-8")).decode("utf-8")


def decrypt_api_key(ciphertext: str | None) -> str:
    if not ciphertext:
        return ""
    return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")


async def require_ai_model_config(
    db: AsyncSession,
    *,
    current_user: User,
    config_id: str,
) -> AiModelConfig:
    config = await get_ai_model_config(db, config_id=config_id, user_id=current_user.id)
    if not config:
        raise BusinessException(message="AI model config not found", code=4061, status_code=404)
    return config


async def list_user_ai_model_configs(db: AsyncSession, *, current_user: User) -> list[AiModelConfig]:
    return await list_ai_model_configs(db, user_id=current_user.id)


async def create_user_ai_model_config(
    db: AsyncSession,
    *,
    current_user: User,
    payload: AiModelConfigCreateRequest,
) -> AiModelConfig:
    if payload.is_default:
        await clear_default_ai_model_configs(db, user_id=current_user.id)
    return await insert_ai_model_config(
        db,
        config_id=build_ai_model_config_id(),
        user_id=current_user.id,
        label=payload.label,
        provider=payload.provider.strip().lower(),
        base_url=payload.base_url.strip(),
        model_name=payload.model_name.strip(),
        api_key_ciphertext=encrypt_api_key(payload.api_key),
        temperature=payload.temperature,
        context_window=payload.context_window,
        is_default=payload.is_default,
        enabled=payload.enabled,
    )


async def update_user_ai_model_config(
    db: AsyncSession,
    *,
    current_user: User,
    config_id: str,
    payload: AiModelConfigUpdateRequest,
) -> AiModelConfig:
    config = await require_ai_model_config(db, current_user=current_user, config_id=config_id)
    if payload.label is not None:
        config.label = payload.label
    if payload.provider is not None:
        config.provider = payload.provider.strip().lower()
    if payload.base_url is not None:
        config.base_url = payload.base_url.strip()
    if payload.model_name is not None:
        config.model_name = payload.model_name.strip()
    if payload.api_key is not None:
        config.api_key_ciphertext = encrypt_api_key(payload.api_key)
    if payload.temperature is not None:
        config.temperature = payload.temperature
    if payload.context_window is not None:
        config.context_window = payload.context_window
    if payload.enabled is not None:
        config.enabled = payload.enabled
    await db.flush()
    await db.refresh(config)
    return config


async def set_default_ai_model_config(
    db: AsyncSession,
    *,
    current_user: User,
    config_id: str,
) -> AiModelConfig:
    config = await require_ai_model_config(db, current_user=current_user, config_id=config_id)
    if not config.enabled:
        raise BusinessException(message="disabled AI model config cannot be default", code=4062, status_code=400)
    await clear_default_ai_model_configs(db, user_id=current_user.id)
    config.is_default = True
    await db.flush()
    await db.refresh(config)
    return config


async def delete_user_ai_model_config(
    db: AsyncSession,
    *,
    current_user: User,
    config_id: str,
) -> int:
    config = await require_ai_model_config(db, current_user=current_user, config_id=config_id)
    if config.is_default:
        raise BusinessException(message="default AI model config cannot be deleted", code=4063, status_code=400)
    await db.delete(config)
    await db.flush()
    return 1


def ai_model_config_runtime_kwargs(config: AiModelConfig) -> dict:
    return {
        "provider": config.provider,
        "base_url": config.base_url,
        "model": config.model_name,
        "api_key": decrypt_api_key(config.api_key_ciphertext),
        "temperature": config.temperature,
    }
