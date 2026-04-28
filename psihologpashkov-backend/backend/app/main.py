from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.api.v1.router import api_v1_router
from app.core.config import Settings, get_settings
from app.schemas.health import RootResponse


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
    app.state.settings = app_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    )

    uploads_root = Path(app_settings.uploads_root)
    uploads_root.mkdir(parents=True, exist_ok=True)

    app.mount(
        app_settings.uploads_public_path,
        StaticFiles(directory=uploads_root),
        name="uploads",
    )

    @app.get("/", response_model=RootResponse, tags=["root"])
    async def root() -> RootResponse:
        return RootResponse(
            app=app_settings.app_name,
            status="ok",
            docs_url="/docs",
            health_url=f"{app_settings.api_v1_prefix}/healthz",
        )

    app.include_router(api_v1_router, prefix=app_settings.api_v1_prefix)

    return app


app = create_app()
