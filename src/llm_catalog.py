"""Shared LiteLLM model catalog and model identifier helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

LOCAL_GGUF_PROVIDER = "local-gguf"
_OPENAI_ALIAS_PREFIXES = ("gpt-", "o1-", "o3-", "o4-", "o5-")


@dataclass(frozen=True)
class RemoteModel:
    """Descriptor for a cloud model exposed through liteLLM."""

    name: str
    path: str
    provider: str


REMOTE_MODELS: tuple[RemoteModel, ...] = (
    RemoteModel(name="GPT-5.4 nano", path="openai/gpt-5.4-nano", provider="openai"),
    RemoteModel(name="GPT-5.4 mini", path="openai/gpt-5.4-mini", provider="openai"),
    RemoteModel(
        name="Claude Sonnet 4.6",
        path="anthropic/claude-sonnet-4-6",
        provider="anthropic",
    ),
    RemoteModel(
        name="Claude Haiku 4.5",
        path="anthropic/claude-haiku-4-5",
        provider="anthropic",
    ),
    RemoteModel(
        name="Gemini 2.5 Flash-Lite",
        path="gemini/gemini-2.5-flash-lite",
        provider="gemini",
    ),
    RemoteModel(
        name="DeepSeek Chat", path="deepseek/deepseek-chat", provider="deepseek"
    ),
)


def get_remote_models() -> list[RemoteModel]:
    """Return the curated list of API models shown in the UI."""
    return list(REMOTE_MODELS)


def is_openai_alias(model_name: str) -> bool:
    """Return True for legacy OpenAI model names without a provider prefix."""
    return any(model_name.startswith(prefix) for prefix in _OPENAI_ALIAS_PREFIXES)


def is_local_model_identifier(model_name: str) -> bool:
    """Return True if *model_name* points to a local GGUF file."""
    path = Path(model_name)
    return path.suffix.lower() == ".gguf" or path.exists()


def local_provider_model_name(model_path: str) -> str:
    """Wrap a local GGUF path so liteLLM routes it to the custom provider."""
    return f"{LOCAL_GGUF_PROVIDER}/{model_path}"


def extract_local_model_path(model_name: str) -> str:
    """Return the raw GGUF path from a local liteLLM model identifier."""
    prefix = f"{LOCAL_GGUF_PROVIDER}/"
    if model_name.startswith(prefix):
        return model_name[len(prefix) :]
    return model_name


def normalize_model_name(model_name: str) -> str:
    """Normalize legacy identifiers to the provider/model format expected by liteLLM."""
    if is_local_model_identifier(model_name):
        return local_provider_model_name(model_name)
    if is_openai_alias(model_name):
        return f"openai/{model_name}"
    return model_name


def is_api_model_identifier(model_name: str) -> bool:
    """Return True if *model_name* should be handled by liteLLM as an API model."""
    normalized = normalize_model_name(model_name)
    return not normalized.startswith(f"{LOCAL_GGUF_PROVIDER}/") and "/" in normalized
