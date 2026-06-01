"""Tests for cache management."""

import pytest

from src.cache import CacheManager


@pytest.fixture
def cache_manager(temp_dir):
    """Create a cache manager for testing."""
    return CacheManager(cache_dir=temp_dir / "cache")


def test_cache_set_and_get(cache_manager):
    """Test basic cache set and get operations."""
    test_data = {"key": "value", "number": 123}

    cache_manager.set("test_key", "test_prompt", "test_model", test_data)

    result = cache_manager.get("test_key", "test_prompt", "test_model")

    assert result is not None
    assert result["data"] == test_data


def test_cache_miss(cache_manager):
    """Test cache miss scenario."""
    result = cache_manager.get("nonexistent", "prompt", "model")
    assert result is None


def test_cache_key_generation(cache_manager):
    """Test cache key generation."""
    key1 = cache_manager._get_cache_key("word", "prompt", "model")
    key2 = cache_manager._get_cache_key("word", "prompt", "model")
    key3 = cache_manager._get_cache_key("word", "different_prompt", "model")

    assert key1 == key2  # Same inputs should generate same key
    assert key1 != key3  # Different inputs should generate different keys


def test_cache_cleanup(cache_manager):
    """Test cache cleanup functionality."""
    cache_manager.set("test1", "prompt", "model", {"data": "test1"})
    cache_manager.set("test2", "prompt", "model", {"data": "test2"})

    cleaned = cache_manager.cleanup_expired()
    assert isinstance(cleaned, int)


def test_cache_statistics(cache_manager):
    """Test cache statistics."""
    cache_manager.set("word1", "prompt", "model", {"data": "word1"})

    stats = cache_manager.get_cache_stats()

    assert "total_entries" in stats
    assert "valid_entries" in stats
    assert "expired_entries" in stats
    assert stats["total_entries"] >= 1
