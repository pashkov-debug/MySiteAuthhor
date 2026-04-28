from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_app_settings, get_user_repository
from app.core.config import Settings
from app.schemas.auth import LoginRequest, RegisterRequest, TokenPairResponse
from app.schemas.user import UserPublic
from app.services.auth_service import (
    InactiveUserError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserRepository,
    authenticate_user,
    create_token_pair,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> object:
    try:
        return await register_user(data, user_repository)
    except (UserAlreadyExistsError, IntegrityError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        ) from exc


@router.post("/login", response_model=TokenPairResponse)
async def login(
    data: LoginRequest,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> TokenPairResponse:
    try:
        user = await authenticate_user(data, user_repository)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        ) from exc

    token_pair = create_token_pair(user.id, settings)

    return TokenPairResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type="bearer",
        expires_in=token_pair.expires_in,
    )
