from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=100, description="用户名")
    display_name: str | None = Field(default=None, max_length=255, description="展示名称")


class UserData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str | None = None
    avatar_url: str
    created_at: datetime
    last_login_at: datetime | None = None


class UserCreateData(UserData):
    default_knowledge_base_id: str = Field(..., description="默认知识库ID")


class UserListData(BaseModel):
    items: list[UserData]
    total: int
