from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from conf.database import get_write_database
from conf.logging import app_logger
from crud.auth_user import create_user_account, update_user_last_login_at
from crud.knowledge_base import get_or_create_default_knowledge_base
from crud.user import get_user_by_username
from models.user import User
from schemas.auth import LoginRequest, RegisterRequest, UserAuthResponse
from services.graph_projection_service import sync_knowledge_base_projection, sync_user_projection
from schemas.users import UserPublic
from utils.auth import get_current_user
from utils.response import success_response
from utils.security import create_access_token, hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register_user(
        payload: RegisterRequest,
        db: AsyncSession = Depends(get_write_database),
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

    knowledge_base = await get_or_create_default_knowledge_base(
        db,
        user_id=account.id,
    )
    await sync_user_projection(user=account)
    await sync_knowledge_base_projection(user=account, knowledge_base=knowledge_base)

    data = UserPublic.model_validate(account)
    return success_response(data=data, message="register success")


@router.post("/login")
async def login_user(
        payload: LoginRequest,
        db: AsyncSession = Depends(get_write_database),
):
    log = app_logger.bind(module="auth")

    user = await get_user_by_username(db, username=payload.username)

    if not user:
        log.warning("auth.login.failed username={} reason=user_not_found", payload.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not verify_password(payload.password, user.password_hash):
        log.warning(
            "auth.login.failed username={} user_id={} reason=wrong_password",
            payload.username,
            user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    user = await update_user_last_login_at(db, user_id=user.id)
    if not user:
        log.error(
            "auth.login.failed username={} reason=user_missing_after_update",
            payload.username,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    await sync_user_projection(user=user)

    token = await create_access_token(subject=str(user.id))

    log.info(
        "auth.login.succeeded user_id={} username={}",
        user.id,
        user.username,
    )

    data = UserAuthResponse(access_token=token)
    return success_response(data=data, message="login success")


@router.get("/me")
async def get_current_user_profile(
        current_user: User = Depends(get_current_user),
):
    data = UserPublic.model_validate(current_user)
    return success_response(data=data)
