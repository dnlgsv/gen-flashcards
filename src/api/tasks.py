"""Background task management: TaskStore and generation worker."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .schemas import GenerateRequest, TaskStatusEnum

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class TaskEvent:
    """A single progress event emitted during generation."""

    event_type: str
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Task:
    """State for a single generation job."""

    task_id: str
    status: TaskStatusEnum
    total_words: int
    processed_words: int
    events: list[TaskEvent]
    result: list[dict[str, Any]] | None
    error: str | None
    created_at: datetime
    updated_at: datetime
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


# ---------------------------------------------------------------------------
# TaskStore
# ---------------------------------------------------------------------------


class TaskStore:
    """Thread-safe in-memory store for generation tasks."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._store_lock = threading.Lock()

    def create(self, task_id: str, total_words: int) -> Task:
        now = datetime.now(UTC)
        task = Task(
            task_id=task_id,
            status=TaskStatusEnum.pending,
            total_words=total_words,
            processed_words=0,
            events=[],
            result=None,
            error=None,
            created_at=now,
            updated_at=now,
        )
        with self._store_lock:
            self._tasks[task_id] = task
        return task

    def get(self, task_id: str) -> Task | None:
        with self._store_lock:
            return self._tasks.get(task_id)

    def push_event(self, task_id: str, event_type: str, data: dict[str, Any]) -> None:
        task = self.get(task_id)
        if task is None:
            return
        event = TaskEvent(event_type=event_type, data=data)
        with task._lock:
            task.events.append(event)
            if event_type in {"word_complete", "word_error"}:
                task.processed_words += 1
            if task.status == TaskStatusEnum.pending:
                task.status = TaskStatusEnum.running
            task.updated_at = datetime.now(UTC)

    def complete(self, task_id: str, result: list[dict[str, Any]]) -> None:
        task = self.get(task_id)
        if task is None:
            return
        with task._lock:
            task.status = TaskStatusEnum.completed
            task.result = result
            task.updated_at = datetime.now(UTC)

    def fail(self, task_id: str, error: str) -> None:
        task = self.get(task_id)
        if task is None:
            return
        with task._lock:
            task.status = TaskStatusEnum.failed
            task.error = error
            task.updated_at = datetime.now(UTC)

    def cleanup_old(self, max_age_hours: int = 24) -> int:
        """Remove completed/failed tasks older than max_age_hours."""
        now = datetime.now(UTC)
        to_remove: list[str] = []
        with self._store_lock:
            for tid, task in self._tasks.items():
                if task.status in (TaskStatusEnum.completed, TaskStatusEnum.failed):
                    age = (now - task.updated_at).total_seconds() / 3600
                    if age > max_age_hours:
                        to_remove.append(tid)
            for tid in to_remove:
                del self._tasks[tid]
        return len(to_remove)


# Module-level singleton used by routers via Depends(get_task_store)
task_store = TaskStore()


# ---------------------------------------------------------------------------
# Background generation worker (runs in llm_executor thread)
# ---------------------------------------------------------------------------


def run_generation(
    task_id: str,
    request: GenerateRequest,
    store: TaskStore,
) -> None:
    """Blocking generation function. Designed to run in llm_executor (max_workers=1).

    Calls lower-level AnkiCardsGenerator methods directly to emit per-word
    progress events to the TaskStore, which the SSE stream can deliver to
    the Next.js frontend in real time.

    NOTE: This is intentionally a regular (non-async) function. It must NOT
    call asyncio.get_event_loop() — it runs on a non-asyncio executor thread.
    """
    # Lazy import to avoid circular: app.py → routers → tasks → main → ...
    from src.main import (  # noqa: PLC0415
        AnkiCardsGenerator,
        load_prompt,
        prompt_with_learner_level,
    )

    try:
        store.push_event(task_id, "word_start", {"message": "Initializing generator…"})

        generator = AnkiCardsGenerator(
            tts_provider=request.tts_provider,
            tts_model=request.tts_model,
            language=request.language,
            speaker=request.speaker,
            target_language=request.target_language,
            enable_images=request.enable_images,
            image_provider=request.image_provider,
            image_model=request.image_model,
        )
        prompt = prompt_with_learner_level(load_prompt(), request.learner_level)
        cards: list[dict[str, Any]] = []

        for idx, word in enumerate(request.words):
            store.push_event(
                task_id,
                "word_start",
                {"word": word, "index": idx + 1, "total": len(request.words)},
            )
            try:
                card_data = generator.get_expression_card_info(
                    request.model_name, prompt, word
                )
                if request.enable_audio:
                    card_data = generator._generate_audio_files(  # noqa: SLF001
                        card_data, word, request.audio_format
                    )
                if request.enable_images:
                    card_data = generator._generate_image(card_data, word)  # noqa: SLF001
                generator._save_card_data(card_data, word)  # noqa: SLF001
                cards.append(card_data)
                store.push_event(
                    task_id,
                    "word_complete",
                    {
                        "word": word,
                        "index": idx + 1,
                        "total": len(request.words),
                        "card": card_data,
                    },
                )
            except Exception as word_exc:
                store.push_event(
                    task_id,
                    "word_error",
                    {
                        "word": word,
                        "index": idx + 1,
                        "total": len(request.words),
                        "error": str(word_exc),
                    },
                )

        if not cards:
            store.fail(task_id, "All words failed to generate")
            store.push_event(
                task_id, "failed", {"error": "All words failed to generate"}
            )
        else:
            store.complete(task_id, cards)
            store.push_event(
                task_id,
                "complete",
                {
                    "total_cards": len(cards),
                    "skipped": len(request.words) - len(cards),
                },
            )

    except Exception as exc:
        store.fail(task_id, str(exc))
        store.push_event(task_id, "failed", {"error": str(exc)})
