"""Test configuration and fixtures."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from src.config import Config


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_config(temp_dir: Path) -> Config:
    """Create a test configuration."""
    return Config(
        data_dir=temp_dir / "data",
        audio_dir=temp_dir / "audio",
        processed_expressions_dir=temp_dir / "processed",
        json_dir=temp_dir / "json",
        anki_decks_dir=temp_dir / "anki",
        cache_dir=temp_dir / "cache",
    )


@pytest.fixture
def sample_words():
    """Sample words for testing."""
    return ["example", "test", "vocabulary"]


@pytest.fixture
def sample_card_data():
    """Sample card data for testing."""
    return {
        "expression": "example",
        "original_form": "example",
        "definition": "A thing characteristic of its kind or illustrating a general rule.",
        "examples": ["This is an example sentence."],
        "synonyms": ["instance", "sample"],
        "antonyms": [],
        "collocations": ["for example", "example of"],
        "part_of_speech": "noun",
        "translations": ["пример"],
        "topics": ["general"],
        "audio_expression": "",
        "audio_definition": "",
        "audio_examples": "",
    }
