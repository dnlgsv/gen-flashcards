"""Custom exceptions for the LM Anki Cards Creator application."""


class AnkiCardsCreatorError(Exception):
    """Base exception class for the application."""

    pass


class ModelError(AnkiCardsCreatorError):
    """Exception raised for model-related errors."""

    pass


class ModelLoadError(ModelError):
    """Exception raised when model fails to load."""

    pass


class ModelInferenceError(ModelError):
    """Exception raised when model inference fails."""

    pass


class AudioError(AnkiCardsCreatorError):
    """Exception raised for audio processing errors."""

    pass


class AudioGenerationError(AudioError):
    """Exception raised when audio generation fails."""

    pass


class ImageError(AnkiCardsCreatorError):
    """Exception raised for image generation errors."""

    pass


class ImageGenerationError(ImageError):
    """Exception raised when image generation fails."""

    pass


class ConfigurationError(AnkiCardsCreatorError):
    """Exception raised for configuration-related errors."""

    pass


class FileProcessingError(AnkiCardsCreatorError):
    """Exception raised for file processing errors."""

    pass


class CacheError(AnkiCardsCreatorError):
    """Exception raised for cache-related errors."""

    pass


class ValidationError(AnkiCardsCreatorError):
    """Exception raised for data validation errors."""

    pass


class APIError(AnkiCardsCreatorError):
    """Exception raised for external API errors."""

    pass


class AnkiDeckError(AnkiCardsCreatorError):
    """Exception raised for Anki deck creation errors."""

    pass
