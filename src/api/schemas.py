"""API-layer Pydantic schemas (request/response models).

These are distinct from src.schemas.CardInfo which is the LLM output schema.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.media_catalog import (
    is_valid_image_model,
    is_valid_tts_model,
    is_valid_tts_voice,
)

CardType = Literal["recognition", "reverse", "production", "cloze"]


def _default_card_types() -> list[CardType]:
    return ["recognition"]


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    """Request body for POST /api/generate."""

    words: list[str]
    model_name: str
    deck_name: str = "Vocabulary Deck"
    tts_provider: Literal["qwen3", "openai", "google"] = "qwen3"
    tts_model: str | None = None
    language: str = "en"
    target_language: str = "ru"
    speaker: str = "Vivian"
    audio_format: Literal["mp3", "wav"] = "mp3"
    learner_level: Literal["auto", "A1", "A2", "B1", "B2", "C1", "C2"] = "auto"
    enable_audio: bool = True
    enable_images: bool = True
    image_provider: Literal["local", "openai", "google"] = "local"
    image_model: str | None = None

    @field_validator("words")
    @classmethod
    def words_not_empty(cls, v: list[str]) -> list[str]:
        cleaned = [w.strip() for w in v if w.strip()]
        if not cleaned:
            raise ValueError("words list must contain at least one non-empty word")
        if len(cleaned) > 100:
            raise ValueError("words list must not exceed 100 items")
        return cleaned

    @model_validator(mode="after")
    def validate_media_compatibility(self) -> GenerateRequest:
        if self.enable_audio and not is_valid_tts_model(
            self.tts_provider, self.tts_model
        ):
            raise ValueError(
                f"Unsupported TTS model '{self.tts_model}' for provider '{self.tts_provider}'"
            )
        if self.enable_audio and not is_valid_tts_voice(
            self.tts_provider, self.speaker
        ):
            raise ValueError(
                f"Unsupported speaker '{self.speaker}' for provider '{self.tts_provider}'"
            )
        if self.enable_images and not is_valid_image_model(
            self.image_provider, self.image_model
        ):
            raise ValueError(
                f"Unsupported image model '{self.image_model}' for provider '{self.image_provider}'"
            )
        return self


class BuildDeckRequest(BaseModel):
    """Request body for POST /api/deck/build."""

    cards_data: list[dict[str, Any]]
    deck_name: str = "Vocabulary Deck"
    card_types: list[CardType] = Field(default_factory=_default_card_types)
    task_id: str | None = None  # Optional link to the generating task

    @field_validator("cards_data")
    @classmethod
    def cards_not_empty(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not v:
            raise ValueError("cards_data must not be empty")
        seen: dict[str, str] = {}
        duplicates: list[str] = []
        for card in v:
            expression = str(card.get("expression", "")).strip()
            if not expression:
                continue
            key = expression.casefold()
            if key in seen:
                duplicates.append(expression)
            else:
                seen[key] = expression
        if duplicates:
            duplicate_list = ", ".join(sorted(set(duplicates), key=str.casefold))
            raise ValueError(f"duplicate card expression(s): {duplicate_list}")
        return v

    @field_validator("card_types")
    @classmethod
    def card_types_not_empty(cls, v: list[CardType]) -> list[CardType]:
        if not v:
            raise ValueError("card_types must contain at least one item")
        return list(dict.fromkeys(v))


class TTSRequest(BaseModel):
    """Request body for POST /api/tts/generate."""

    text: str
    language: str = "en"
    provider: Literal["qwen3", "openai", "google"] = "qwen3"
    model: str | None = None
    speaker: str = "Vivian"
    response_format: Literal["mp3", "wav"] = "mp3"

    @model_validator(mode="after")
    def validate_provider_settings(self) -> TTSRequest:
        if not is_valid_tts_model(self.provider, self.model):
            raise ValueError(
                f"Unsupported TTS model '{self.model}' for provider '{self.provider}'"
            )
        if not is_valid_tts_voice(self.provider, self.speaker):
            raise ValueError(
                f"Unsupported speaker '{self.speaker}' for provider '{self.provider}'"
            )
        return self


class RegenerateCardFieldRequest(BaseModel):
    """Request body for regenerating one text field on an existing card."""

    card: dict[str, Any]
    field: Literal["definition", "examples"]
    model_name: str
    learner_level: Literal["auto", "A1", "A2", "B1", "B2", "C1", "C2"] = "auto"
    target_language: str = "ru"

    @field_validator("card")
    @classmethod
    def card_has_expression(cls, v: dict[str, Any]) -> dict[str, Any]:
        if not str(v.get("expression", "")).strip():
            raise ValueError("card.expression must not be empty")
        return v


class RegenerateCardImageRequest(BaseModel):
    """Request body for regenerating one card image."""

    card: dict[str, Any]
    provider: Literal["local", "openai", "google"] = "local"
    model: str | None = None

    @field_validator("card")
    @classmethod
    def image_card_has_expression(cls, v: dict[str, Any]) -> dict[str, Any]:
        if not str(v.get("expression", "")).strip():
            raise ValueError("card.expression must not be empty")
        return v

    @model_validator(mode="after")
    def validate_image_settings(self) -> RegenerateCardImageRequest:
        if not is_valid_image_model(self.provider, self.model):
            raise ValueError(
                f"Unsupported image model '{self.model}' for provider '{self.provider}'"
            )
        return self


class DetectLanguageRequest(BaseModel):
    """Request body for POST /api/detect-language."""

    text: str


class CandidateExtractRequest(BaseModel):
    """Request body for POST /api/candidates/extract."""

    text: str
    language: str = "en"
    learner_level: Literal["auto", "A1", "A2", "B1", "B2", "C1", "C2"] = "auto"
    target_count: int = 30
    include_phrases: bool = True
    use_model_rerank: bool = False
    model_name: str | None = None

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("text must not be empty")
        if len(cleaned) > 50_000:
            raise ValueError("text must not exceed 50000 characters")
        return cleaned

    @field_validator("target_count")
    @classmethod
    def target_count_reasonable(cls, v: int) -> int:
        if v < 1:
            raise ValueError("target_count must be at least 1")
        if v > 100:
            raise ValueError("target_count must not exceed 100")
        return v


# ---------------------------------------------------------------------------
# Response bodies
# ---------------------------------------------------------------------------


class TaskStatusEnum(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class GenerateResponse(BaseModel):
    """Response for POST /api/generate."""

    task_id: str
    status: TaskStatusEnum
    message: str


class TaskStatusResponse(BaseModel):
    """Response for GET /api/generate/{task_id}."""

    task_id: str
    status: TaskStatusEnum
    total_words: int
    processed_words: int
    progress_pct: float
    result: list[dict[str, Any]] | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class ModelInfo(BaseModel):
    """Information about a single available model."""

    name: str
    path: str
    provider: str
    loaded: bool


class ModelsResponse(BaseModel):
    """Response for GET /api/models."""

    models: list[ModelInfo]


class BuildDeckResponse(BaseModel):
    """Response for POST /api/deck/build."""

    filename: str
    deck_name: str
    card_count: int
    download_url: str


class ImportDeckResponse(BaseModel):
    """Response for POST /api/deck/import."""

    deck_name: str
    card_count: int
    cards: list[dict[str, Any]]


class TTSResponse(BaseModel):
    """Response for POST /api/tts/generate."""

    filename: str
    url: str


class RegenerateCardFieldResponse(BaseModel):
    """Response for regenerating one text field on an existing card."""

    field: Literal["definition", "examples"]
    value: str | list[str]


class RegenerateCardImageResponse(BaseModel):
    """Response for regenerating one card image."""

    filename: str
    url: str
    image: str


class DetectLanguageResponse(BaseModel):
    """Response for POST /api/detect-language."""

    language: str | None  # ISO-639-1 code, or None if detection failed
    language_name: str | None


class Candidate(BaseModel):
    """A ranked word or phrase candidate extracted from text."""

    expression: str
    kind: Literal["word", "phrase"]
    score: float
    frequency: int
    contexts: list[str]
    reason: str


class CandidateExtractResponse(BaseModel):
    """Response for POST /api/candidates/extract."""

    candidates: list[Candidate]


class CacheStatsResponse(BaseModel):
    """Response for GET /api/cache/stats."""

    total_entries: int
    valid_entries: int
    expired_entries: int
    total_size_bytes: int
    cache_dir: str


class HealthResponse(BaseModel):
    """Response for GET /health."""

    status: Literal["ok"] = "ok"
    version: str
    device: str
    loaded_models: list[str]
    cache_enabled: bool


class PreflightCheck(BaseModel):
    """A single setup/configuration check."""

    name: str
    status: Literal["ok", "warning", "error"]
    message: str


class PreflightResponse(BaseModel):
    """Response for GET /api/preflight."""

    ready: bool
    checks: list[PreflightCheck]
