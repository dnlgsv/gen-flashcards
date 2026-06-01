"""Tests for configuration management."""

import builtins
from pathlib import Path

import pytest

from src.config import Config


def test_config_initialization(test_config):
    """Test config initialization."""
    assert isinstance(test_config.data_dir, Path)
    assert test_config.device in ["cpu", "cuda", "mps"]
    assert test_config.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]


def test_config_creates_directories(temp_dir):
    """Test that config creates necessary directories."""
    config = Config(data_dir=temp_dir / "test_data")

    assert config.data_dir.exists()
    assert config.audio_dir.exists()
    assert config.processed_expressions_dir.exists()


def test_config_device_detection():
    """Test device detection logic."""
    config = Config()

    assert config.device in ["cpu", "cuda", "mps"]


def test_config_device_detection_falls_back_when_torch_import_fails(monkeypatch):
    """Torch import/load failures should not prevent config initialization."""
    real_import = builtins.__import__

    def import_with_torch_failure(name, *args, **kwargs):
        if name == "torch":
            raise PermissionError("torch dll blocked")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_with_torch_failure)

    config = Config()

    assert config.device == "cpu"


def test_config_environment_variables(temp_dir, monkeypatch):
    """Test loading from environment variables."""
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    config = Config.from_env()
    assert config.log_level == "DEBUG"
    assert config.openai_api_key == "test-key-123"


def test_config_data_dir_from_env(temp_dir, monkeypatch):
    """DATA_DIR should move all runtime subdirectories together."""
    data_dir = temp_dir / "runtime"
    monkeypatch.setenv("DATA_DIR", str(data_dir))

    config = Config.from_env()

    assert config.data_dir == data_dir
    assert config.audio_dir == data_dir / "audio"
    assert config.images_dir == data_dir / "images"
    assert config.cache_dir == data_dir / "cache"
    assert config.audio_dir.exists()


def test_config_enable_images_false_from_env(monkeypatch):
    """ENABLE_IMAGES=false should disable image generation."""
    monkeypatch.setenv("ENABLE_IMAGES", "false")

    config = Config.from_env()

    assert config.enable_images is False


def test_config_processing_settings():
    """Test processing settings have valid defaults."""
    config = Config()
    assert config.max_retries > 0
    assert isinstance(config.enable_caching, bool)
    assert config.retry_delay >= 0


def test_config_rejects_incompatible_image_model():
    config = Config(
        model_path="openai/gpt-5.4-nano",
        image_provider="openai",
        image_model="gemini/gemini-3.1-flash-image-preview",
    )

    with pytest.raises(ValueError, match="Unsupported image model"):
        config.validate()


def test_config_rejects_incompatible_tts_model():
    config = Config(
        model_path="openai/gpt-5.4-nano",
        tts_provider="google",
        tts_model="openai/tts-1",
    )

    with pytest.raises(ValueError, match="Unsupported TTS model"):
        config.validate()
