"""Tests for src/tts.py — TextToSpeechService."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.tts import TextToSpeechService


@pytest.fixture
def tts():
    return TextToSpeechService()


# ---------------------------------------------------------------------------
# _prepare_text
# ---------------------------------------------------------------------------


def test_prepare_text_string(tts):
    assert tts._prepare_text("hello") == "hello"


def test_prepare_text_list(tts):
    assert tts._prepare_text(["hello", "world"]) == "hello world"


def test_prepare_text_list_filters_empty(tts):
    assert tts._prepare_text(["hello", "", "world"]) == "hello world"


def test_prepare_text_empty_string(tts):
    assert tts._prepare_text("") == ""


def test_prepare_text_empty_list(tts):
    assert tts._prepare_text([]) == ""


# ---------------------------------------------------------------------------
# generate_audio — file already exists
# ---------------------------------------------------------------------------


def test_generate_audio_skips_existing_file(tts, temp_dir):
    # TTS always produces WAV; create the .wav file directly
    filepath = str(temp_dir / "existing.wav")
    Path(filepath).write_bytes(b"fake audio")

    result = tts.generate_audio("some text", filepath)
    assert result == filepath


# ---------------------------------------------------------------------------
# generate_audio — Qwen3 successful generation
# ---------------------------------------------------------------------------


def test_generate_audio_success(tts, temp_dir):
    filepath = str(temp_dir / "output.wav")

    with (
        patch("src.tts.QWEN3_TTS_AVAILABLE", True),
        patch.object(tts, "_load_qwen3_model") as mock_load,
        patch("src.tts.sf") as mock_sf,
        patch("src.tts.config") as mock_cfg,
    ):
        mock_cfg.max_retries = 3
        mock_cfg.retry_delay = 0
        mock_cfg.qwen3_tts_instruct = "Speak clearly."
        mock_model = MagicMock()
        mock_model.generate_custom_voice.return_value = ([b"wav_data"], 22050)
        mock_load.return_value = mock_model

        result = tts.generate_audio("hello world", filepath)

    assert result == filepath
    mock_model.generate_custom_voice.assert_called_once()
    mock_sf.write.assert_called_once()


# ---------------------------------------------------------------------------
# generate_audio — empty text returns ""
# ---------------------------------------------------------------------------


def test_generate_audio_empty_text_returns_empty(tts, temp_dir):
    filepath = str(temp_dir / "empty.wav")
    result = tts.generate_audio("", filepath)
    assert result == ""


def test_generate_audio_empty_list_returns_empty(tts, temp_dir):
    filepath = str(temp_dir / "empty2.wav")
    result = tts.generate_audio([], filepath)
    assert result == ""


# ---------------------------------------------------------------------------
# generate_audio — retry on transient failure
# ---------------------------------------------------------------------------


def test_generate_audio_retries_on_failure(tts, temp_dir):
    filepath = str(temp_dir / "retry.wav")
    call_count = 0

    def flaky_generate(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise OSError("transient error")
        return ([b"wav_data"], 22050)

    with (
        patch("src.tts.QWEN3_TTS_AVAILABLE", True),
        patch.object(tts, "_load_qwen3_model") as mock_load,
        patch("src.tts.sf"),
        patch("src.tts.config") as mock_cfg,
    ):
        mock_cfg.max_retries = 3
        mock_cfg.retry_delay = 0
        mock_cfg.qwen3_tts_instruct = "Speak clearly."
        mock_model = MagicMock()
        mock_model.generate_custom_voice.side_effect = flaky_generate
        mock_load.return_value = mock_model

        result = tts.generate_audio("hello", filepath)

    assert call_count == 2
    assert result == filepath


def test_generate_audio_openai_success(temp_dir):
    filepath = str(temp_dir / "openai.mp3")
    service = TextToSpeechService(
        provider="openai",
        model="openai/tts-1",
        speaker="alloy",
    )

    with (
        patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True),
        patch("litellm.speech") as mock_speech,
    ):
        mock_response = MagicMock()
        mock_response.stream_to_file.side_effect = lambda path: Path(path).write_bytes(
            b"audio"
        )
        mock_speech.return_value = mock_response

        result = service.generate_audio("hello world", filepath)

    assert result == filepath
    assert Path(filepath).read_bytes() == b"audio"
    mock_speech.assert_called_once()


def test_generate_audio_google_success(temp_dir):
    filepath = str(temp_dir / "google.mp3")
    service = TextToSpeechService(
        provider="google",
        model="gemini/gemini-2.5-flash-preview-tts",
        speaker="Kore",
    )

    with (
        patch.dict("os.environ", {"GEMINI_API_KEY": "gem-test"}, clear=True),
        patch("litellm.speech") as mock_speech,
    ):
        mock_response = MagicMock()
        mock_response.stream_to_file.side_effect = lambda path: Path(path).write_bytes(
            b"audio"
        )
        mock_speech.return_value = mock_response

        result = service.generate_audio("hello world", filepath)

    assert result == filepath
    assert Path(filepath).read_bytes() == b"audio"
    mock_speech.assert_called_once()
