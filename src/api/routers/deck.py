"""POST /api/deck/build and GET /api/deck/{filename}/download endpoints."""

from __future__ import annotations

import asyncio
import re
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from src.config import Config

from ..dependencies import get_config, get_io_executor
from ..schemas import BuildDeckRequest, BuildDeckResponse, ImportDeckResponse

router = APIRouter(tags=["Deck"])

# Allowlist: only hex-prefixed .apkg filenames produced by this API
_SAFE_FILENAME_RE = re.compile(r"^deck_[a-f0-9]{8}\.apkg$")
_MAX_IMPORT_BYTES = 100 * 1024 * 1024


@router.post("/deck/build", response_model=BuildDeckResponse)
async def build_deck(
    body: BuildDeckRequest,
    cfg: Config = Depends(get_config),
    io_exec: ThreadPoolExecutor = Depends(get_io_executor),
) -> BuildDeckResponse:
    """Build an .apkg Anki deck from card data and serve it locally."""
    filename = f"deck_{uuid.uuid4().hex[:8]}.apkg"
    output_path = str(cfg.anki_decks_dir / filename)

    def _build() -> None:
        from src.main import AnkiCardsGenerator  # noqa: PLC0415

        gen = AnkiCardsGenerator()
        gen.create_anki_package(
            body.cards_data,
            body.deck_name,
            output_path,
            card_types=body.card_types,
        )

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(io_exec, _build)

    download_url = f"/api/deck/{filename}/download"

    return BuildDeckResponse(
        filename=filename,
        deck_name=body.deck_name,
        card_count=len(body.cards_data) * len(body.card_types),
        download_url=download_url,
    )


@router.post("/deck/import", response_model=ImportDeckResponse)
async def import_deck(
    request: Request,
    filename: str = "deck.apkg",
    cfg: Config = Depends(get_config),
    io_exec: ThreadPoolExecutor = Depends(get_io_executor),
) -> ImportDeckResponse:
    """Import cards from an uploaded .apkg deck."""
    if not filename.lower().endswith(".apkg"):
        raise HTTPException(status_code=400, detail="Only .apkg files can be imported")

    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > _MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="Deck file is too large")

    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="No deck file uploaded")
    if len(data) > _MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="Deck file is too large")

    def _import() -> dict:
        from src.anki_utils import import_anki_package  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as temp_dir:
            upload_path = Path(temp_dir) / "upload.apkg"
            upload_path.write_bytes(data)
            return import_anki_package(upload_path, cfg.audio_dir, cfg.images_dir)

    loop = asyncio.get_running_loop()
    imported = await loop.run_in_executor(io_exec, _import)
    return ImportDeckResponse(**imported)


@router.get("/deck/{filename}/download")
async def download_deck(
    filename: str,
    cfg: Config = Depends(get_config),
) -> FileResponse:
    """Stream a locally built .apkg file to the client (fallback route)."""
    # Path traversal guard
    if not _SAFE_FILENAME_RE.match(filename):
        raise HTTPException(status_code=400, detail="Invalid filename format")

    file_path = cfg.anki_decks_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Deck file not found: {filename}")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )
