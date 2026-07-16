from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AiModelProviderPreset(BaseModel):
    provider: str
    label: str
    base_url: str
    model_name: str


class AiModelConfigData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: int
    label: str
    provider: str
    base_url: str
    model_name: str
    temperature: float
    context_window: int
    is_default: bool
    enabled: bool
    has_api_key: bool
    created_at: datetime
    updated_at: datetime


class AiModelConfigListData(BaseModel):
    provider_presets: list[AiModelProviderPreset]
    items: list[AiModelConfigData]
    default_config_id: str | None = None


class AiModelConfigCreateRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=120)
    provider: str = Field(..., min_length=1, max_length=64)
    base_url: str = Field(..., min_length=1, max_length=500)
    model_name: str = Field(..., min_length=1, max_length=255)
    api_key: str | None = Field(default=None, max_length=4096)
    temperature: float = Field(default=0.0, ge=0, le=2)
    context_window: int = Field(default=64000, ge=1000, le=1000000)
    is_default: bool = False
    enabled: bool = True


class AiModelConfigUpdateRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    provider: str | None = Field(default=None, min_length=1, max_length=64)
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    model_name: str | None = Field(default=None, min_length=1, max_length=255)
    api_key: str | None = Field(default=None, max_length=4096)
    temperature: float | None = Field(default=None, ge=0, le=2)
    context_window: int | None = Field(default=None, ge=1000, le=1000000)
    enabled: bool | None = None


class AiModelConfigTestData(BaseModel):
    config_id: str
    ok: bool
    message: str
