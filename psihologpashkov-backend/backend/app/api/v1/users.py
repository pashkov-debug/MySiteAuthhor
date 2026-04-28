from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.schemas.user import UserPublic
from app.services.auth_service import UserForAuth

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserPublic)
async def read_me(
    current_user: Annotated[UserForAuth, Depends(get_current_user)],
) -> object:
    return current_user
