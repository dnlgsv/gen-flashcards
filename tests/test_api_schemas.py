"""Tests for provider/model validation in API schemas."""

import pytest
from pydantic import ValidationError

from src.api.schemas import (
    BuildDeckRequest,
    CandidateExtractRequest,
    GenerateRequest,
    TTSRequest,
)


def test_generate_request_rejects_incompatible_tts_voice():
    with pytest.raises(ValidationError, match="Unsupported speaker"):
        GenerateRequest(
            words=["apple"],
            model_name="openai/gpt-5.4-nano",
            tts_provider="openai",
            tts_model="openai/tts-1",
            speaker="Vivian",
            image_provider="local",
            image_model="local/stable-diffusion",
        )


def test_generate_request_rejects_incompatible_image_model():
    with pytest.raises(ValidationError, match="Unsupported image model"):
        GenerateRequest(
            words=["apple"],
            model_name="openai/gpt-5.4-nano",
            image_provider="openai",
            image_model="gemini/gemini-3.1-flash-image-preview",
        )


def test_tts_request_rejects_incompatible_model():
    with pytest.raises(ValidationError, match="Unsupported TTS model"):
        TTSRequest(
            text="hello",
            provider="google",
            model="openai/tts-1",
            speaker="Kore",
        )


def test_build_deck_request_rejects_duplicate_expressions():
    with pytest.raises(ValidationError, match="duplicate card expression"):
        BuildDeckRequest(
            deck_name="Duplicates",
            cards_data=[
                {"expression": "Apple", "definition": "a fruit"},
                {"expression": " apple ", "definition": "same fruit"},
            ],
        )


def test_candidate_extract_request_rejects_empty_text():
    with pytest.raises(ValidationError, match="text must not be empty"):
        CandidateExtractRequest(text="  ")


def test_candidate_extract_request_rejects_large_target_count():
    with pytest.raises(ValidationError, match="target_count"):
        CandidateExtractRequest(text="hello world", target_count=101)
