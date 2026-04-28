from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_refresh_session_repository, get_user_repository
from app.schemas.user import UserPasswordChangeRequest, UserPublic, UserUpdateRequest
from app.services.auth_service import UserForAuth
from app.services.refresh_session_service import RefreshSessionRepository
from app.services.user_service import (
    InvalidCurrentPasswordError,
    NewPasswordMustDifferError,
    UserNotFoundError,
    UserProfileRepository,
    change_current_user_password,
    update_current_user_profile,
)

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserPublic)
async def read_me(
    current_user: Annotated[UserForAuth, Depends(get_current_user)],
) -> object:
    return current_user


@router.patch("/me", response_model=UserPublic)
async def update_me(
    data: UserUpdateRequest,
    current_user: Annotated[UserForAuth, Depends(get_current_user)],
    user_repository: Annotated[UserProfileRepository, Depends(get_user_repository)],
) -> object:
    try:
        return await update_current_user_profile(
            user_id=current_user.id,
            data=data,
            user_repository=user_repository,
        )
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        ) from exc


@router.patch("/me/password", response_model=UserPublic)
async def change_me_password(
    data: UserPasswordChangeRequest,
    current_user: Annotated[UserForAuth, Depends(get_current_user)],
    user_repository: Annotated[UserProfileRepository, Depends(get_user_repository)],
    refresh_session_repository: Annotated[
        RefreshSessionRepository,
        Depends(get_refresh_session_repository),
    ],
) -> object:
    try:
        return await change_current_user_password(
            current_user=current_user,
            data=data,
            user_repository=user_repository,
            refresh_session_repository=refresh_session_repository,
        )
    except InvalidCurrentPasswordError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid current password",
        ) from exc
    except NewPasswordMustDifferError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from current password",
        ) from exc
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        ) from exc
