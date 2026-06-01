"""Logging configuration and utilities."""

import logging
import sys
from pathlib import Path

try:
    from .config import config
except ImportError:
    # Fallback for script execution
    from src.config import config


def setup_logging(
    log_level: str | None = None,
    log_file: Path | None = None,
    log_format: str | None = None,
) -> logging.Logger:
    """Set up logging configuration for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
        log_format: Optional custom log format string

    Returns:
        Configured logger instance
    """
    # Use config defaults if not provided
    log_level = log_level or config.log_level
    log_format = log_format or config.log_format

    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(numeric_level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.

    Args:
        name: Logger name, typically __name__

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes."""

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(self.__class__.__module__ + "." + self.__class__.__name__)


# Set up default logging
setup_logging()
