"""GET /api/models endpoint — list available LLM models."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from src.config import Config
from src.llm_catalog import get_remote_models
from src.model_manager import ModelManager

from ..dependencies import get_config, get_model_manager
from ..schemas import ModelInfo, ModelsResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Models"])


@router.get("/models", response_model=ModelsResponse)
async def list_models(
    cfg: Config = Depends(get_config),
    mm: ModelManager = Depends(get_model_manager),
) -> ModelsResponse:
    """Return all available models (local GGUF files + liteLLM API models)."""
    loaded = set(mm.get_loaded_models())
    models: list[ModelInfo] = []

    # ── Local GGUF files ─────────────────────────────────────────────────────
    try:
        gguf_files = sorted(cfg.models_dir.glob("*.gguf"))
    except (FileNotFoundError, OSError) as exc:
        logger.warning("Could not scan models dir %s: %s", cfg.models_dir, exc)
        gguf_files = []

    for f in gguf_files:
        models.append(
            ModelInfo(
                name=f.stem,
                path=str(f),
                provider="local",
                loaded=(str(f) in loaded),
            )
        )

    # ── API models via liteLLM ────────────────────────────────────────────────
    for remote_model in get_remote_models():
        models.append(
            ModelInfo(
                name=remote_model.name,
                path=remote_model.path,
                provider=remote_model.provider,
                loaded=False,
            )
        )

    return ModelsResponse(models=models)
