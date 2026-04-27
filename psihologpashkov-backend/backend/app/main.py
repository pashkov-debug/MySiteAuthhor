from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()

    docs_url = "/docs" if app_settings.enable_openapi else None
    redoc_url = "/redoc" if app_settings.enable_openapi else None
    openapi_url = "/openapi.json" if app_settings.enable_openapi else None

    app = FastAPI(
        title=app_settings.app_name,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    )

    app.include_router(api_v1_router, prefix=app_settings.api_v1_prefix)

    return app


app = create_app()
