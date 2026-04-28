from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_app_settings, get_refresh_session_repository, get_user_repository
from app.core.config import Settings
from app.schemas.auth import (
    LoginRequest,
    LogoutResponse,
    RefreshTokenRequest,
    RegisterRequest,
    TokenPairResponse,
)
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
from app.services.refresh_session_service import (
    InvalidRefreshSessionError,
    InvalidRefreshTokenError,
    RefreshSessionRepository,
    logout_refresh_token,
    refresh_token_pair,
    store_refresh_token,
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
    request: Request,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    refresh_session_repository: Annotated[
        RefreshSessionRepository,
        Depends(get_refresh_session_repository),
    ],
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

    await store_refresh_token(
        refresh_token=token_pair.refresh_token,
        refresh_session_repository=refresh_session_repository,
        settings=settings,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    return TokenPairResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type="bearer",
        expires_in=token_pair.expires_in,
    )


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    data: RefreshTokenRequest,
    request: Request,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    refresh_session_repository: Annotated[
        RefreshSessionRepository,
        Depends(get_refresh_session_repository),
    ],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> TokenPairResponse:
    try:
        token_pair = await refresh_token_pair(
            refresh_token=data.refresh_token,
            user_repository=user_repository,
            refresh_session_repository=refresh_session_repository,
            settings=settings,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except (InvalidRefreshTokenError, InvalidRefreshSessionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        ) from exc

    return TokenPairResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type="bearer",
        expires_in=token_pair.expires_in,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    data: RefreshTokenRequest,
    refresh_session_repository: Annotated[
        RefreshSessionRepository,
        Depends(get_refresh_session_repository),
    ],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> LogoutResponse:
    await logout_refresh_token(
        refresh_token=data.refresh_token,
        refresh_session_repository=refresh_session_repository,
        settings=settings,
    )

    return LogoutResponse()
