"""GET /health endpoint."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends

from src.config import Config
from src.llm_catalog import is_api_model_identifier, is_local_model_identifier
from src.media_catalog import (
    IMAGE_PROVIDER_GOOGLE,
    IMAGE_PROVIDER_LOCAL,
    IMAGE_PROVIDER_OPENAI,
    TTS_PROVIDER_GOOGLE,
    TTS_PROVIDER_OPENAI,
)
from src.model_manager import ModelManager

from ..dependencies import get_config, get_model_manager
from ..schemas import HealthResponse, PreflightCheck, PreflightResponse

router = APIRouter(tags=["Health"])

_API_VERSION = "2.0.0"


@router.get("/health", response_model=HealthResponse)
async def health_check(
    mm: ModelManager = Depends(get_model_manager),
    cfg: Config = Depends(get_config),
) -> HealthResponse:
    """Liveness/readiness probe. Always open — no auth required."""
    return HealthResponse(
        version=_API_VERSION,
        device=cfg.device,
        loaded_models=mm.get_loaded_models(),
        cache_enabled=cfg.enable_caching,
    )


@router.get("/api/preflight", response_model=PreflightResponse)
async def preflight_check(cfg: Config = Depends(get_config)) -> PreflightResponse:
    """Return actionable setup checks for the local app."""
    checks = [
        _check_model(cfg),
        _check_tts(cfg),
        _check_images(cfg),
        _check_runtime_dirs(cfg),
    ]
    return PreflightResponse(
        ready=all(check.status != "error" for check in checks),
        checks=checks,
    )


def _check_model(cfg: Config) -> PreflightCheck:
    if is_local_model_identifier(cfg.model_path):
        if not os.path.exists(cfg.model_path):
            return PreflightCheck(
                name="model",
                status="error",
                message=f"Local model file not found: {cfg.model_path}",
            )
        return PreflightCheck(
            name="model",
            status="ok",
            message=f"Local model file found: {cfg.model_path}",
        )

    if is_api_model_identifier(cfg.model_path):
        provider = cfg.model_path.split("/", 1)[0]
        required = {
            "openai": ["OPENAI_API_KEY"],
            "anthropic": ["ANTHROPIC_API_KEY"],
            "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
            "deepseek": ["DEEPSEEK_API_KEY"],
        }.get(provider, [])
        if required and not any(os.getenv(name) for name in required):
            return PreflightCheck(
                name="model",
                status="error",
                message=f"Missing {' or '.join(required)} for {cfg.model_path}",
            )
        return PreflightCheck(
            name="model",
            status="ok",
            message=f"API model configured: {cfg.model_path}",
        )

    return PreflightCheck(
        name="model",
        status="error",
        message="MODEL_PATH must be a local .gguf path or provider/model id.",
    )


def _check_tts(cfg: Config) -> PreflightCheck:
    if cfg.tts_provider == TTS_PROVIDER_OPENAI and not os.getenv("OPENAI_API_KEY"):
        return PreflightCheck(
            name="tts",
            status="error",
            message="OPENAI_API_KEY is required for OpenAI TTS.",
        )
    if cfg.tts_provider == TTS_PROVIDER_GOOGLE and not os.getenv("GEMINI_API_KEY"):
        return PreflightCheck(
            name="tts",
            status="error",
            message="GEMINI_API_KEY is required for Google TTS.",
        )
    return PreflightCheck(
        name="tts",
        status="ok",
        message=f"TTS provider configured: {cfg.tts_provider}",
    )


def _check_images(cfg: Config) -> PreflightCheck:
    if not cfg.enable_images:
        return PreflightCheck(
            name="images",
            status="ok",
            message="Image generation is disabled.",
        )
    if cfg.image_provider == IMAGE_PROVIDER_LOCAL and not cfg.sd_model_path.exists():
        return PreflightCheck(
            name="images",
            status="error",
            message=f"Stable Diffusion model file not found: {cfg.sd_model_path}",
        )
    if cfg.image_provider == IMAGE_PROVIDER_OPENAI and not os.getenv("OPENAI_API_KEY"):
        return PreflightCheck(
            name="images",
            status="error",
            message="OPENAI_API_KEY is required for OpenAI image generation.",
        )
    if cfg.image_provider == IMAGE_PROVIDER_GOOGLE and not os.getenv("GEMINI_API_KEY"):
        return PreflightCheck(
            name="images",
            status="error",
            message="GEMINI_API_KEY is required for Google image generation.",
        )
    return PreflightCheck(
        name="images",
        status="ok",
        message=f"Image provider configured: {cfg.image_provider}",
    )


def _check_runtime_dirs(cfg: Config) -> PreflightCheck:
    missing = [
        path
        for path in (
            cfg.data_dir,
            cfg.audio_dir,
            cfg.images_dir,
            cfg.anki_decks_dir,
            cfg.processed_expressions_dir,
        )
        if not path.exists()
    ]
    if missing:
        return PreflightCheck(
            name="runtime_dirs",
            status="error",
            message=f"Missing runtime directories: {', '.join(str(path) for path in missing)}",
        )
    return PreflightCheck(
        name="runtime_dirs",
        status="ok",
        message="Runtime directories are available.",
    )
