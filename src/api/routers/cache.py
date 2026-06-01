"""GET /api/cache/stats and DELETE /api/cache endpoints."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException

from src.cache import CacheManager

from ..dependencies import get_cache_manager, get_io_executor
from ..schemas import CacheStatsResponse

router = APIRouter(tags=["Cache"])


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    cm: CacheManager = Depends(get_cache_manager),
    io_exec: ThreadPoolExecutor = Depends(get_io_executor),
) -> CacheStatsResponse:
    """Return cache usage statistics."""
    loop = asyncio.get_running_loop()
    stats: dict = await loop.run_in_executor(io_exec, cm.get_cache_stats)

    if "error" in stats:
        raise HTTPException(status_code=500, detail=stats["error"])

    return CacheStatsResponse(**stats)


@router.delete("/cache", status_code=204)
async def clear_cache(
    cm: CacheManager = Depends(get_cache_manager),
    io_exec: ThreadPoolExecutor = Depends(get_io_executor),
) -> None:
    """Delete all cached LLM responses."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(io_exec, cm.clear)
