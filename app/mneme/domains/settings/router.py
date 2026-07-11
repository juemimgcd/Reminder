from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.database import get_database, get_write_database
from app.mneme.domains.settings.ai_models import (
    create_user_ai_model_config,
    delete_user_ai_model_config,
    list_user_ai_model_configs,
    provider_presets,
    require_ai_model_config,
    set_default_ai_model_config,
    update_user_ai_model_config,
)
from app.mneme.models.user import User
from app.mneme.schemas.ai_model_config import (
    AiModelConfigCreateRequest,
    AiModelConfigData,
    AiModelConfigListData,
    AiModelConfigTestData,
    AiModelConfigUpdateRequest,
)
from app.mneme.utils.auth import get_current_user
from app.mneme.utils.response import success_response


router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/ai-models")
async def list_ai_model_configs_api(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    configs = await list_user_ai_model_configs(db, current_user=current_user)
    items = [AiModelConfigData.model_validate(config) for config in configs]
    default_config = next((item for item in items if item.is_default), None)
    return success_response(
        data=AiModelConfigListData(
            provider_presets=provider_presets(),
            items=items,
            default_config_id=default_config.id if default_config else None,
        )
    )


@router.post("/ai-models")
async def create_ai_model_config_api(
    payload: AiModelConfigCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    config = await create_user_ai_model_config(db, current_user=current_user, payload=payload)
    return success_response(data=AiModelConfigData.model_validate(config), message="AI model config created")


@router.patch("/ai-models/{config_id}")
async def update_ai_model_config_api(
    config_id: str,
    payload: AiModelConfigUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    config = await update_user_ai_model_config(db, current_user=current_user, config_id=config_id, payload=payload)
    return success_response(data=AiModelConfigData.model_validate(config), message="AI model config updated")


@router.post("/ai-models/{config_id}/test")
async def test_ai_model_config_api(
    config_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    config = await require_ai_model_config(db, current_user=current_user, config_id=config_id)
    ok = bool(config.enabled and config.base_url and config.model_name and config.has_api_key)
    message = "AI model config is ready." if ok else "AI model config is incomplete."
    return success_response(data=AiModelConfigTestData(config_id=config.id, ok=ok, message=message))


@router.post("/ai-models/{config_id}/default")
async def set_default_ai_model_config_api(
    config_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    config = await set_default_ai_model_config(db, current_user=current_user, config_id=config_id)
    return success_response(data=AiModelConfigData.model_validate(config), message="default AI model config updated")


@router.delete("/ai-models/{config_id}")
async def delete_ai_model_config_api(
    config_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    deleted_count = await delete_user_ai_model_config(db, current_user=current_user, config_id=config_id)
    return success_response(data={"config_id": config_id, "deleted_count": deleted_count}, message="AI model config deleted")
