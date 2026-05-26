from pydantic import BaseModel, ConfigDict


class UserPublic(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    avatar_url: str

    model_config = ConfigDict(from_attributes=True)


class UserAdminPublic(BaseModel):
    """
    管理员视角的用户信息（用于后台管理）
    """

    id: int
    username: str
    display_name: str | None = None
    avatar_url: str

    model_config = ConfigDict(from_attributes=True)
