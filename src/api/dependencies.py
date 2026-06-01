"""FastAPI dependency injection providers."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi import Request

from src.cache import CacheManager, cache_manager
from src.config import Config, config
from src.model_manager import ModelManager, model_manager

from .tasks import TaskStore, task_store


def get_config() -> Config:
    return config


def get_model_manager() -> ModelManager:
    return model_manager


def get_cache_manager() -> CacheManager:
    return cache_manager


def get_task_store() -> TaskStore:
    return task_store


def get_llm_executor(request: Request) -> ThreadPoolExecutor:
    return request.app.state.llm_executor  # type: ignore[no-any-return]


def get_io_executor(request: Request) -> ThreadPoolExecutor:
    return request.app.state.io_executor  # type: ignore[no-any-return]
