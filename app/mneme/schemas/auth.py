from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str


class UserAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
