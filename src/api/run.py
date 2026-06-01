"""Uvicorn entry point for the FastAPI application.

Run with:
    uv run python src/api/run.py
or:
    uv run uvicorn src.api.run:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

from src.api.app import create_app

# Module-level app instance for uvicorn's import path
app = create_app()


def main() -> None:
    """CLI entry point registered as ``anki-api`` in pyproject.toml."""
    import uvicorn  # noqa: PLC0415

    uvicorn.run(
        "src.api.run:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
