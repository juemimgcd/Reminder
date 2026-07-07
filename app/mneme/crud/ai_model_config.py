from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.models.ai_model_config import AiModelConfig


async def create_ai_model_config(
    db: AsyncSession,
    *,
    config_id: str,
    user_id: int,
    label: str,
    provider: str,
    base_url: str,
    model_name: str,
    api_key_ciphertext: str | None,
    temperature: float,
    context_window: int,
    is_default: bool,
    enabled: bool,
) -> AiModelConfig:
    config = AiModelConfig(
        id=config_id,
        user_id=user_id,
        label=label,
        provider=provider,
        base_url=base_url,
        model_name=model_name,
        api_key_ciphertext=api_key_ciphertext,
        temperature=temperature,
        context_window=context_window,
        is_default=is_default,
        enabled=enabled,
    )
    db.add(config)
    await db.flush()
    await db.refresh(config)
    return config


async def get_ai_model_config(
    db: AsyncSession,
    *,
    config_id: str,
    user_id: int,
) -> AiModelConfig | None:
    result = await db.execute(select(AiModelConfig).where(AiModelConfig.id == config_id, AiModelConfig.user_id == user_id))
    return result.scalar_one_or_none()


async def get_default_ai_model_config(
    db: AsyncSession,
    *,
    user_id: int,
) -> AiModelConfig | None:
    result = await db.execute(
        select(AiModelConfig).where(
            AiModelConfig.user_id == user_id,
            AiModelConfig.is_default.is_(True),
            AiModelConfig.enabled.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def list_ai_model_configs(
    db: AsyncSession,
    *,
    user_id: int,
) -> list[AiModelConfig]:
    result = await db.execute(
        select(AiModelConfig)
        .where(AiModelConfig.user_id == user_id)
        .order_by(AiModelConfig.is_default.desc(), AiModelConfig.created_at.asc())
    )
    return list(result.scalars().all())


async def clear_default_ai_model_configs(
    db: AsyncSession,
    *,
    user_id: int,
) -> None:
    await db.execute(
        update(AiModelConfig)
        .where(AiModelConfig.user_id == user_id, AiModelConfig.is_default.is_(True))
        .values(is_default=False)
    )
