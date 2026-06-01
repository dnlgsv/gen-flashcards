"""POST /api/tts/generate endpoint — single-text TTS preview."""

from __future__ import annotations

import asyncio
import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from src.config import Config
from src.tts import TextToSpeechService

from ..dependencies import get_config, get_io_executor
from ..schemas import TTSRequest, TTSResponse

router = APIRouter(tags=["TTS"])


@router.post("/tts/generate", response_model=TTSResponse)
async def generate_tts(
    body: TTSRequest,
    cfg: Config = Depends(get_config),
    io_exec: ThreadPoolExecutor = Depends(get_io_executor),
) -> TTSResponse:
    """Generate TTS audio for a single text snippet (used for card preview)."""
    # Stable filename: same text+options → same file, skip regeneration
    key = (
        f"{body.text}:{body.language}:{body.provider}:{body.model or ''}:"
        f"{body.speaker}:{body.response_format}"
    )
    text_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
    ext = "wav" if body.provider == "qwen3" else body.response_format
    filename = f"preview_{text_hash}.{ext}"
    filepath = str(cfg.audio_dir / filename)

    def _gen() -> str | None:
        svc = TextToSpeechService(
            provider=body.provider,
            language=body.language,
            speaker=body.speaker,
            model=body.model,
        )
        return svc.generate_audio(body.text, filepath)

    loop = asyncio.get_running_loop()
    actual_path: str | None = await loop.run_in_executor(io_exec, _gen)

    if not actual_path:
        raise HTTPException(status_code=500, detail="TTS generation produced no output")

    # Qwen3 may return a .wav path regardless of the requested extension
    actual_filename = Path(actual_path).name
    return TTSResponse(
        filename=actual_filename,
        url=f"/static/audio/{actual_filename}",
    )
