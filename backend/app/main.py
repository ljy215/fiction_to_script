from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.files import router as files_router
from app.api.generation import router as generation_router
from app.api.health import router as health_router
from app.api.imports import router as imports_router
from app.api.projects import router as projects_router
from app.config import get_settings
from app.db import init_db


def create_app() -> FastAPI:
    settings = get_settings()
    settings.ensure_local_directories()
    init_db()

    app = FastAPI(
        title=settings.app_name,
        description="FastAPI backend for the AI novel-to-script MVP.",
        version=settings.app_version,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(files_router)
    app.include_router(generation_router)
    app.include_router(health_router)
    app.include_router(imports_router)
    app.include_router(projects_router)
    return app


app = create_app()
