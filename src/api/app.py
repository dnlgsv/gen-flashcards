"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.config import config
from src.exceptions import (
    AnkiCardsCreatorError,
    AnkiDeckError,
    APIError,
    AudioError,
    AudioGenerationError,
    CacheError,
    ConfigurationError,
    FileProcessingError,
    ModelError,
    ModelInferenceError,
    ModelLoadError,
    ValidationError,
)
from src.logger import setup_logging

from .routers import (
    cache,
    candidates,
    cards,
    deck,
    detect,
    generate,
    health,
    models,
    tts,
)
from .tasks import task_store

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_FRONTEND_STATIC_DIRS = [
    _PROJECT_ROOT / "frontend" / "out",
    Path(__file__).resolve().parent / "static_frontend",
]

# Map custom exceptions → HTTP status codes (most-specific first)
_EXCEPTION_STATUS_MAP: list[tuple[type[Exception], int]] = [
    (ModelLoadError, 503),
    (ModelInferenceError, 502),
    (ModelError, 500),
    (AudioGenerationError, 500),
    (AudioError, 500),
    (ConfigurationError, 500),
    (FileProcessingError, 422),
    (CacheError, 500),
    (AnkiDeckError, 422),
    (ValidationError, 422),
    (APIError, 502),
    (AnkiCardsCreatorError, 500),
]


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Application lifespan: create resources on startup, release on shutdown."""
    setup_logging()
    logger.info("Starting Anki Cards API v2.0.0")

    # LLM executor: max_workers=1 serialises all LLM/model-loading calls.
    # GPU has a single VRAM budget; ModelManager._instances is not protected
    # against concurrent access during model loading.
    app.state.llm_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="llm")

    # IO executor: TTS (Qwen3), file I/O, Anki packing.
    app.state.io_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="io")

    # Background task: clean up stale completed/failed jobs once per hour.
    cleanup_task = asyncio.create_task(_cleanup_loop())

    logger.info("Executors ready. Serving requests.")
    yield

    # Shutdown
    cleanup_task.cancel()
    app.state.llm_executor.shutdown(wait=False)
    app.state.io_executor.shutdown(wait=False)
    logger.info("Executors shut down.")


async def _cleanup_loop() -> None:
    """Periodically remove old completed/failed tasks from the in-memory store."""
    while True:
        await asyncio.sleep(3600)
        removed = task_store.cleanup_old(max_age_hours=24)
        if removed:
            logger.info("Cleaned up %d stale tasks", removed)


def create_app() -> FastAPI:
    """Application factory — instantiate and configure the FastAPI app."""
    app = FastAPI(
        title="Anki Cards API",
        version="2.0.0",
        description=(
            "REST API for the LM Anki Cards Creator. "
            "Generates flashcard data from words using LLMs and TTS."
        ),
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # CORS — allow Next.js dev server and configurable production origin
    # ------------------------------------------------------------------
    frontend_url = os.getenv("FRONTEND_URL", "")
    allow_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]
    if frontend_url:
        allow_origins.append(frontend_url)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    # ------------------------------------------------------------------
    # Static file serving for generated audio files
    # ------------------------------------------------------------------
    config.audio_dir.mkdir(parents=True, exist_ok=True)
    try:
        app.mount(
            "/static/audio",
            StaticFiles(directory=str(config.audio_dir)),
            name="audio",
        )
    except RuntimeError as exc:  # pragma: no cover
        logger.warning("Could not mount static audio dir: %s", exc)

    # Static file serving for generated images
    config.images_dir.mkdir(parents=True, exist_ok=True)
    try:
        app.mount(
            "/static/images",
            StaticFiles(directory=str(config.images_dir)),
            name="images",
        )
    except RuntimeError as exc:  # pragma: no cover
        logger.warning("Could not mount static images dir: %s", exc)

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------
    app.include_router(health.router)  # GET /health
    app.include_router(models.router, prefix="/api")  # GET /api/models
    # generate: /stream route registered before /{task_id} inside the router
    app.include_router(generate.router, prefix="/api")  # /api/generate/*
    app.include_router(deck.router, prefix="/api")  # /api/deck/*
    app.include_router(candidates.router, prefix="/api")  # /api/candidates/*
    app.include_router(cards.router, prefix="/api")  # /api/cards/*
    app.include_router(tts.router, prefix="/api")  # /api/tts/*
    app.include_router(detect.router, prefix="/api")  # /api/detect-language
    app.include_router(cache.router, prefix="/api")  # /api/cache/*

    # ------------------------------------------------------------------
    # Bundled local web UI
    # ------------------------------------------------------------------
    frontend_dir = next((path for path in _FRONTEND_STATIC_DIRS if path.exists()), None)
    if frontend_dir:
        logger.info("Serving bundled frontend from %s", frontend_dir)
        app.mount(
            "/",
            StaticFiles(directory=str(frontend_dir), html=True),
            name="frontend",
        )
    else:
        logger.warning(
            "Bundled frontend not found. Run `npm run build:local` in frontend/ "
            "or use `anki-api` for API-only mode."
        )

    # ------------------------------------------------------------------
    # Global exception handler for custom exceptions
    # ------------------------------------------------------------------
    @app.exception_handler(AnkiCardsCreatorError)
    async def anki_exception_handler(
        request: Request, exc: AnkiCardsCreatorError
    ) -> JSONResponse:
        status_code = 500
        for exc_type, code in _EXCEPTION_STATUS_MAP:
            if isinstance(exc, exc_type):
                status_code = code
                break
        logger.error("Application error [%d]: %s", status_code, exc)
        return JSONResponse({"detail": str(exc)}, status_code=status_code)

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse({"detail": "Internal server error"}, status_code=500)

    return app
