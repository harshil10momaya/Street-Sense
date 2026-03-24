"""
StreetSense — FastAPI Application Entry Point

Configures the app with:
- Async lifespan (startup/shutdown hooks)
- CORS middleware
- Request logging middleware
- Static file serving for uploads
- All API routers
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import close_db, init_db


# ─── Lifespan (replaces deprecated on_event) ───

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # === STARTUP ===
    setup_logging()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")

    # Ensure upload directory exists
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Upload directory: {settings.upload_path}")

    # Initialize database tables (dev mode)
    if settings.environment == "development":
        try:
            await init_db()
            logger.info("Database tables initialized")
        except Exception as e:
            logger.warning(f"Database init skipped (not connected): {e}")

    logger.info("StreetSense is ready")

    yield  # App runs here

    # === SHUTDOWN ===
    logger.info("Shutting down StreetSense...")
    await close_db()
    logger.info("Database connections closed")


# ─── App Factory ───

def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""

    app = FastAPI(
        title=settings.app_name,
        description=(
            "AI-Powered Road Monitoring & Smart Complaint Management System. "
            "Detects potholes, cracks, garbage, and manholes using YOLOv8 + MiDaS "
            "depth estimation, with automatic severity scoring and complaint routing."
        ),
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ─── CORS ───
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── Request Logging Middleware ───
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.debug(f"→ {request.method} {request.url.path}")
        response = await call_next(request)
        logger.debug(f"← {response.status_code} {request.url.path}")
        return response

    # ─── Global Exception Handler ───
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "type": type(exc).__name__,
            },
        )

    # ─── Static Files (uploaded images) ───
    upload_path = settings.upload_path
    if upload_path.exists():
        app.mount(
            "/uploads",
            StaticFiles(directory=str(upload_path)),
            name="uploads",
        )

    # ─── Routers ───
    app.include_router(api_router)

    # ─── Root Endpoint ───
    @app.get("/", tags=["root"])
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


# Create the app instance
app = create_app()
