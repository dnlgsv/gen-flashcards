"""Generation endpoints with SSE progress streaming."""

from __future__ import annotations

import asyncio
import json
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..dependencies import get_llm_executor, get_task_store
from ..schemas import (
    GenerateRequest,
    GenerateResponse,
    TaskStatusEnum,
    TaskStatusResponse,
)
from ..tasks import TaskStore, run_generation

router = APIRouter(tags=["Generate"])


def _validate_model_name(model_name: str) -> None:
    """Raise 400 if the model name is clearly invalid."""
    from src.llm_catalog import (  # noqa: PLC0415
        is_api_model_identifier,
        is_local_model_identifier,
    )

    if not model_name:
        raise HTTPException(status_code=400, detail="model_name must not be empty")

    if is_local_model_identifier(model_name):
        from pathlib import Path  # noqa: PLC0415

        if not Path(model_name).exists():
            raise HTTPException(
                status_code=400,
                detail=f"Local model file not found: {model_name}",
            )
        return

    if not is_api_model_identifier(model_name):
        raise HTTPException(
            status_code=400,
            detail=(
                "model_name must be a local .gguf path or a liteLLM identifier like "
                "'openai/gpt-5.4-nano'"
            ),
        )


@router.post("/generate", response_model=GenerateResponse, status_code=202)
async def start_generation(
    body: GenerateRequest,
    store: TaskStore = Depends(get_task_store),
    llm_exec: ThreadPoolExecutor = Depends(get_llm_executor),
) -> GenerateResponse:
    """Queue a card-generation job and immediately return a task_id."""
    _validate_model_name(body.model_name)

    task_id = str(uuid.uuid4())
    store.create(task_id, total_words=len(body.words))

    loop = asyncio.get_running_loop()
    loop.run_in_executor(llm_exec, run_generation, task_id, body, store)

    return GenerateResponse(
        task_id=task_id,
        status=TaskStatusEnum.pending,
        message=f"Generation queued for {len(body.words)} word(s). "
        f"Stream progress at /api/generate/{task_id}/stream",
    )


@router.get("/generate/{task_id}/stream")
async def stream_generation(
    task_id: str,
    request: Request,
    store: TaskStore = Depends(get_task_store),
) -> StreamingResponse:
    """Stream real-time generation progress with Server-Sent Events."""
    if store.get(task_id) is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    async def event_generator():  # type: ignore[return]
        yield "retry: 2000\n\n"

        last_index = 0
        keepalive_ticks = 0

        while True:
            if await request.is_disconnected():
                break

            task = store.get(task_id)
            if task is None:
                payload = json.dumps({"detail": "task not found"})
                yield f"event: error\ndata: {payload}\n\n"
                break

            new_events = task.events[last_index:]
            for ev in new_events:
                data = json.dumps(
                    {
                        "type": ev.event_type,
                        "data": ev.data,
                        "processed": task.processed_words,
                        "total": task.total_words,
                        "timestamp": ev.timestamp.isoformat(),
                    }
                )
                yield f"event: {ev.event_type}\ndata: {data}\n\n"
            last_index += len(new_events)

            if task.status == TaskStatusEnum.completed:
                final = json.dumps(
                    {"task_id": task_id, "total_cards": len(task.result or [])}
                )
                yield f"event: complete\ndata: {final}\n\n"
                break
            if task.status == TaskStatusEnum.failed:
                err = json.dumps({"task_id": task_id, "error": task.error})
                yield f"event: failed\ndata: {err}\n\n"
                break

            keepalive_ticks += 1
            if keepalive_ticks % 30 == 0:
                yield ": keepalive\n\n"

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/generate/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    store: TaskStore = Depends(get_task_store),
) -> TaskStatusResponse:
    """Return current task status. Useful when SSE is unavailable."""
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    pct = (task.processed_words / task.total_words * 100) if task.total_words else 0.0

    return TaskStatusResponse(
        task_id=task_id,
        status=task.status,
        total_words=task.total_words,
        processed_words=task.processed_words,
        progress_pct=round(pct, 1),
        result=task.result,
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
