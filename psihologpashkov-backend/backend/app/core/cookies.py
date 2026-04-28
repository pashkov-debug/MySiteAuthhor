from fastapi import Response

from app.core.config import Settings


def set_refresh_token_cookie(
    response: Response,
    refresh_token: str,
    settings: Settings,
) -> None:
    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=refresh_token,
        max_age=settings.jwt_refresh_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.auth_refresh_cookie_secure,
        samesite=settings.auth_refresh_cookie_samesite,
        domain=settings.auth_refresh_cookie_domain,
        path=settings.auth_refresh_cookie_path,
    )


def clear_refresh_token_cookie(
    response: Response,
    settings: Settings,
) -> None:
    response.delete_cookie(
        key=settings.auth_refresh_cookie_name,
        domain=settings.auth_refresh_cookie_domain,
        path=settings.auth_refresh_cookie_path,
        secure=settings.auth_refresh_cookie_secure,
        httponly=True,
        samesite=settings.auth_refresh_cookie_samesite,
    )
