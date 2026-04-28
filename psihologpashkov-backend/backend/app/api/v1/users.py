from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import (
    get_app_settings,
    get_current_user,
    get_refresh_session_repository,
    get_user_repository,
)
from app.core.config import Settings
from app.core.storage import (
    AvatarFileTooLargeError,
    EmptyAvatarFileError,
    StorageError,
    UnsupportedAvatarExtensionError,
    delete_avatar_by_public_path,
    save_avatar_content,
)
from app.schemas.user import UserPasswordChangeRequest, UserPublic, UserUpdateRequest
from app.services.auth_service import UserForAuth
from app.services.refresh_session_service import RefreshSessionRepository
from app.services.user_service import (
    InvalidCurrentPasswordError,
    NewPasswordMustDifferError,
    UserNotFoundError,
    UserProfileRepository,
    change_current_user_password,
    update_current_user_avatar,
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


@router.patch("/me/avatar", response_model=UserPublic)
async def upload_me_avatar(
    file: Annotated[UploadFile, File()],
    current_user: Annotated[UserForAuth, Depends(get_current_user)],
    user_repository: Annotated[UserProfileRepository, Depends(get_user_repository)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> object:
    content = await file.read()
    old_avatar_path = getattr(current_user, "avatar_path", None)

    try:
        avatar_path = save_avatar_content(
            user_id=current_user.id,
            original_filename=file.filename or "",
            content=content,
            settings=settings,
        )
        updated_user = await update_current_user_avatar(
            user_id=current_user.id,
            avatar_path=avatar_path,
            user_repository=user_repository,
        )
    except UnsupportedAvatarExtensionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported avatar file extension",
        ) from exc
    except EmptyAvatarFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar file must not be empty",
        ) from exc
    except AvatarFileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Avatar file is too large",
        ) from exc
    except UserNotFoundError as exc:
        if "avatar_path" in locals():
            delete_avatar_by_public_path(avatar_path, settings)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        ) from exc
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid avatar file",
        ) from exc

    delete_avatar_by_public_path(old_avatar_path, settings)

    return updated_user


@router.delete("/me/avatar", response_model=UserPublic)
async def delete_me_avatar(
    current_user: Annotated[UserForAuth, Depends(get_current_user)],
    user_repository: Annotated[UserProfileRepository, Depends(get_user_repository)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> object:
    old_avatar_path = getattr(current_user, "avatar_path", None)

    try:
        updated_user = await update_current_user_avatar(
            user_id=current_user.id,
            avatar_path=None,
            user_repository=user_repository,
        )
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        ) from exc

    delete_avatar_by_public_path(old_avatar_path, settings)

    return updated_user
