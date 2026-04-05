from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from conf.database import get_database
from crud.auth_user import create_user_account, update_user_last_login_at
from crud.knowledge_base import get_or_create_default_knowledge_base
from crud.user import get_user_by_username
from models.user import User
from schemas.auth import LoginRequest, RegisterRequest, UserAuthResponse
from schemas.users import UserPublic
from utils.auth import get_current_user
from utils.response import success_response
from utils.security import create_access_token, hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register_user(
        payload: RegisterRequest,
        db: AsyncSession = Depends(get_database),
):
    user = await get_user_by_username(db, username=payload.username)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )

    hashed_password = hash_password(password=payload.password)
    account = await create_user_account(
        db,
        username=payload.username,
        display_name=payload.display_name,
        password_hash=hashed_password,
        avatar_url=None,
    )

    await get_or_create_default_knowledge_base(
        db,
        user_id=account.id,
    )

    data = UserPublic.model_validate(account)
    return success_response(data=data, message="register success")


@router.post("/login")
async def login_user(
        payload: LoginRequest,
        db: AsyncSession = Depends(get_database),
):
    user = await get_user_by_username(db, username=payload.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not verify_password(password=payload.password, password_hash=user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    user = await update_user_last_login_at(
        db,
        user_id=user.id,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    token = await create_access_token(subject=str(user.id))
    data = UserAuthResponse(access_token=token)
    return success_response(data=data, message="login success")


@router.get("/me")
async def get_current_user_profile(
        current_user: User = Depends(get_current_user),
):
    data = UserPublic.model_validate(current_user)
    return success_response(data=data)
