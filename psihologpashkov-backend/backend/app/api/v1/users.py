from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_user_repository
from app.schemas.user import UserPublic, UserUpdateRequest
from app.services.auth_service import UserForAuth, UserRepository
from app.services.user_service import UserNotFoundError, update_current_user_profile

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
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
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
