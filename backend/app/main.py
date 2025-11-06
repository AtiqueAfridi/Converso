"""FastAPI application entry point."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.api.conversation_routes import router as conversation_router
from app.core.config import get_settings


def create_application() -> FastAPI:
    """Instantiate and configure the FastAPI application."""

    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")
    app.include_router(conversation_router, prefix="/api")

    frontend_path = Path(__file__).resolve().parents[2] / "frontend"
    app.mount(
        "/static",
        StaticFiles(directory=str(frontend_path)),
        name="static",
    )

    @app.get("/", include_in_schema=False)
    async def root() -> FileResponse:
        """Serve the single-page chatbot UI."""

        return FileResponse(frontend_path / "index.html")

    return app


app = create_application()
