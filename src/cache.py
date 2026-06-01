"""Cache management for the LM Anki Cards Creator application."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from .config import config
from .exceptions import CacheError
from .logger import LoggerMixin


class CacheManager(LoggerMixin):
    """Manages caching of card data to avoid redundant processing."""

    def __init__(self, cache_dir: Path | None = None, ttl: int = 86400):
        """Initialize cache manager.

        Args:
            cache_dir: Directory to store cache files
            ttl: Time to live for cache entries in seconds (default: 24 hours)
        """
        self.cache_dir = cache_dir or config.cache_dir
        self.ttl = ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Cache manager initialized with directory: {self.cache_dir}")

    def _get_cache_key(self, word: str, prompt: str, model_name: str) -> str:
        """Generate a cache key for the given parameters.

        Args:
            word: The word being processed
            prompt: The prompt used for generation
            model_name: Name of the model used

        Returns:
            Hexadecimal cache key
        """
        key_data = f"{word}:{prompt}:{model_name}".encode()
        return hashlib.sha256(key_data).hexdigest()

    def _get_cache_file(self, cache_key: str) -> Path:
        """Get the cache file path for a given key.

        Args:
            cache_key: The cache key

        Returns:
            Path to the cache file
        """
        return self.cache_dir / f"{cache_key}.json"

    def _is_cache_valid(self, cache_file: Path) -> bool:
        """Check if a cache file is still valid based on TTL.

        Args:
            cache_file: Path to the cache file

        Returns:
            True if cache is valid, False otherwise
        """
        if not cache_file.exists():
            return False

        try:
            file_mtime = cache_file.stat().st_mtime
            current_time = time.time()
            return (current_time - file_mtime) < self.ttl
        except Exception as e:
            self.logger.warning(f"Error checking cache validity: {e}")
            return False

    def get(self, word: str, prompt: str, model_name: str) -> dict[str, Any] | None:
        """Retrieve cached card data if available and valid.

        Args:
            word: The word being processed
            prompt: The prompt used for generation
            model_name: Name of the model used

        Returns:
            Cached card data or None if not found/invalid
        """
        if not config.enable_caching:
            return None

        try:
            cache_key = self._get_cache_key(word, prompt, model_name)
            cache_file = self._get_cache_file(cache_key)

            if not self._is_cache_valid(cache_file):
                self.logger.debug(f"Cache miss for word: {word}")
                return None

            with open(cache_file, encoding="utf-8") as f:
                cached_data = json.load(f)

            self.logger.debug(f"Cache hit for word: {word}")
            return cached_data

        except Exception as e:
            self.logger.warning(f"Error reading cache for word '{word}': {e}")
            return None

    def set(
        self, word: str, prompt: str, model_name: str, card_data: dict[str, Any]
    ) -> None:
        """Cache card data for future use.

        Args:
            word: The word being processed
            prompt: The prompt used for generation
            model_name: Name of the model used
            card_data: The card data to cache
        """
        if not config.enable_caching:
            return

        try:
            cache_key = self._get_cache_key(word, prompt, model_name)
            cache_file = self._get_cache_file(cache_key)

            # Add metadata to cached data
            cached_data = {
                "word": word,
                "model_name": model_name,
                "cached_at": time.time(),
                "data": card_data,
            }

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cached_data, f, indent=2, ensure_ascii=False)

            self.logger.debug(f"Cached data for word: {word}")

        except Exception as e:
            self.logger.warning(f"Error caching data for word '{word}': {e}")
            raise CacheError(f"Failed to cache data: {e}") from e

    def clear(self) -> None:
        """Clear all cached data."""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            self.logger.info("Cache cleared successfully")
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
            raise CacheError(f"Failed to clear cache: {e}") from e

    def cleanup_expired(self) -> int:
        """Remove expired cache entries.

        Returns:
            Number of expired entries removed
        """
        removed_count = 0
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                if not self._is_cache_valid(cache_file):
                    cache_file.unlink()
                    removed_count += 1

            self.logger.info(f"Cleaned up {removed_count} expired cache entries")
            return removed_count

        except Exception as e:
            self.logger.error(f"Error during cache cleanup: {e}")
            raise CacheError(f"Failed to cleanup cache: {e}") from e

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            total_entries = len(cache_files)

            valid_entries = sum(1 for f in cache_files if self._is_cache_valid(f))
            expired_entries = total_entries - valid_entries

            total_size = sum(f.stat().st_size for f in cache_files)

            return {
                "total_entries": total_entries,
                "valid_entries": valid_entries,
                "expired_entries": expired_entries,
                "total_size_bytes": total_size,
                "cache_dir": str(self.cache_dir),
            }

        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}


# Global cache manager instance
cache_manager = CacheManager()
