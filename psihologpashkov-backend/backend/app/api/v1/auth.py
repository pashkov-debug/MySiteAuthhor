from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import (
    get_app_settings,
    get_email_sender,
    get_email_verification_token_repository,
    get_refresh_session_repository,
    get_user_repository,
)
from app.core.config import Settings
from app.core.email import EmailDeliveryError, EmailSender
from app.core.cookies import clear_refresh_token_cookie, set_refresh_token_cookie
from app.schemas.auth import (
    EmailVerificationResendRequest,
    EmailVerificationResponse,
    LoginRequest,
    LogoutResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    TokenPairResponse,
)
from app.services.auth_service import (
    EmailNotVerifiedError,
    InactiveUserError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserRepository,
    authenticate_user,
    create_token_pair,
    register_user,
)
from app.services.email_verification_service import (
    EmailAlreadyVerifiedError,
    EmailVerificationTokenRepository,
    ExpiredEmailVerificationTokenError,
    InvalidEmailVerificationTokenError,
    create_email_verification_token,
    send_registration_verification_email,
    verify_email_by_token,
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
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    verification_token_repository: Annotated[
        EmailVerificationTokenRepository,
        Depends(get_email_verification_token_repository),
    ],
    email_sender: Annotated[EmailSender, Depends(get_email_sender)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> RegisterResponse:
    try:
        user = await register_user(data, user_repository, is_active=False)
    except (UserAlreadyExistsError, IntegrityError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        ) from exc

    verification_token = await create_email_verification_token(
        user=user,
        token_repository=verification_token_repository,
        settings=settings,
    )

    try:
        await send_registration_verification_email(
            user=user,
            raw_token=verification_token.raw_token,
            email_sender=email_sender,
            settings=settings,
        )
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery failed",
        ) from exc

    return RegisterResponse(email=user.email, full_name=user.full_name)


@router.post("/resend-verification", response_model=EmailVerificationResponse)
async def resend_verification_email(
    data: EmailVerificationResendRequest,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    verification_token_repository: Annotated[
        EmailVerificationTokenRepository,
        Depends(get_email_verification_token_repository),
    ],
    email_sender: Annotated[EmailSender, Depends(get_email_sender)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> EmailVerificationResponse:
    user = await user_repository.get_by_email(data.email)

    if user is None or (getattr(user, "email_verified_at", None) is not None and user.is_active):
        return EmailVerificationResponse()

    verification_token = await create_email_verification_token(
        user=user,
        token_repository=verification_token_repository,
        settings=settings,
    )

    try:
        await send_registration_verification_email(
            user=user,
            raw_token=verification_token.raw_token,
            email_sender=email_sender,
            settings=settings,
        )
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery failed",
        ) from exc

    return EmailVerificationResponse()


@router.get("/verify-email", response_model=EmailVerificationResponse)
async def verify_email(
    token: Annotated[str, Query(min_length=1)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    verification_token_repository: Annotated[
        EmailVerificationTokenRepository,
        Depends(get_email_verification_token_repository),
    ],
) -> EmailVerificationResponse:
    try:
        await verify_email_by_token(
            raw_token=token,
            token_repository=verification_token_repository,
            user_repository=user_repository,
        )
    except EmailAlreadyVerifiedError:
        return EmailVerificationResponse()
    except ExpiredEmailVerificationTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Email verification token expired",
        ) from exc
    except InvalidEmailVerificationTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email verification token",
        ) from exc

    return EmailVerificationResponse()


@router.post("/login", response_model=TokenPairResponse)
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
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
    except EmailNotVerifiedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email is not verified",
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

    set_refresh_token_cookie(
        response=response,
        refresh_token=token_pair.refresh_token,
        settings=settings,
    )

    return TokenPairResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type="bearer",
        expires_in=token_pair.expires_in,
    )


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    request: Request,
    response: Response,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    refresh_session_repository: Annotated[
        RefreshSessionRepository,
        Depends(get_refresh_session_repository),
    ],
    settings: Annotated[Settings, Depends(get_app_settings)],
    data: Annotated[RefreshTokenRequest | None, Body()] = None,
) -> TokenPairResponse:
    refresh_token = get_refresh_token_from_request(data, request, settings)

    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    try:
        token_pair = await refresh_token_pair(
            refresh_token=refresh_token,
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

    set_refresh_token_cookie(
        response=response,
        refresh_token=token_pair.refresh_token,
        settings=settings,
    )

    return TokenPairResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type="bearer",
        expires_in=token_pair.expires_in,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    refresh_session_repository: Annotated[
        RefreshSessionRepository,
        Depends(get_refresh_session_repository),
    ],
    settings: Annotated[Settings, Depends(get_app_settings)],
    data: Annotated[RefreshTokenRequest | None, Body()] = None,
) -> LogoutResponse:
    refresh_token = get_refresh_token_from_request(data, request, settings)

    if refresh_token is not None:
        await logout_refresh_token(
            refresh_token=refresh_token,
            refresh_session_repository=refresh_session_repository,
            settings=settings,
        )

    clear_refresh_token_cookie(response=response, settings=settings)

    return LogoutResponse()


def get_refresh_token_from_request(
    data: RefreshTokenRequest | None,
    request: Request,
    settings: Settings,
) -> str | None:
    if data is not None and data.refresh_token:
        return data.refresh_token

    cookie_token = request.cookies.get(settings.auth_refresh_cookie_name)

    if cookie_token and cookie_token.strip():
        return cookie_token

    return None
