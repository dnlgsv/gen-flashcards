"""Per-card regeneration endpoints."""

from __future__ import annotations

import asyncio
import re
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException

from src.config import Config
from src.image_gen import ImageGenerationService
from src.model_manager import model_manager

from ..dependencies import get_config, get_io_executor, get_llm_executor
from ..schemas import (
    RegenerateCardFieldRequest,
    RegenerateCardFieldResponse,
    RegenerateCardImageRequest,
    RegenerateCardImageResponse,
)

router = APIRouter(tags=["Cards"])


def _safe_filename_part(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip().lower())
    return cleaned.strip("_") or "card"


@router.post("/cards/regenerate-field", response_model=RegenerateCardFieldResponse)
async def regenerate_card_field(
    body: RegenerateCardFieldRequest,
    llm_exec: ThreadPoolExecutor = Depends(get_llm_executor),
) -> RegenerateCardFieldResponse:
    """Regenerate a single text field by refreshing the card with the selected LLM."""
    from src.main import (  # noqa: PLC0415
        AnkiCardsGenerator,
        load_prompt,
        prompt_with_learner_level,
    )

    expression = str(body.card["expression"]).strip()
    prompt = prompt_with_learner_level(load_prompt(), body.learner_level)
    target_language = AnkiCardsGenerator._LANGUAGE_NAMES.get(  # noqa: SLF001
        body.target_language.lower(),
        body.target_language.capitalize(),
    )
    resolved_prompt = prompt.replace("{target_language}", target_language)

    def _generate() -> dict:
        return model_manager.generate_card_info(
            body.model_name, resolved_prompt, expression
        )

    loop = asyncio.get_running_loop()
    card_data = await loop.run_in_executor(llm_exec, _generate)
    value = card_data.get(body.field)
    if value is None:
        raise HTTPException(
            status_code=502,
            detail=f"Model response did not include '{body.field}'",
        )

    return RegenerateCardFieldResponse(field=body.field, value=value)


@router.post("/cards/regenerate-image", response_model=RegenerateCardImageResponse)
async def regenerate_card_image(
    body: RegenerateCardImageRequest,
    cfg: Config = Depends(get_config),
    io_exec: ThreadPoolExecutor = Depends(get_io_executor),
) -> RegenerateCardImageResponse:
    """Generate a fresh image for one card and return an Anki image tag."""
    expression = str(body.card["expression"]).strip()
    filename = f"{_safe_filename_part(expression)}_{uuid.uuid4().hex[:8]}.png"
    output_path = cfg.images_dir / filename

    def _generate() -> str:
        service = ImageGenerationService(provider=body.provider, model=body.model)
        return service.generate_image(
            expression=expression,
            definition=str(body.card.get("definition", "")),
            output_path=output_path,
            width=cfg.sd_image_width,
            height=cfg.sd_image_height,
        )

    loop = asyncio.get_running_loop()
    actual_path = await loop.run_in_executor(io_exec, _generate)
    actual_filename = output_path.name if not actual_path else output_path.name
    image_tag = f'<img src="{actual_filename}">'

    return RegenerateCardImageResponse(
        filename=actual_filename,
        url=f"/static/images/{actual_filename}",
        image=image_tag,
    )
