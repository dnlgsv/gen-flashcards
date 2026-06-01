"""Tests for the local browser launcher."""

from __future__ import annotations

import urllib.error

from src import local_app


class _ReadyResponse:
    status = 200

    def __enter__(self) -> _ReadyResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_open_browser_waits_until_url_is_ready(monkeypatch):
    """Browser opens only after the local URL responds."""
    attempts = 0
    opened_urls: list[str] = []

    def fake_urlopen(url: str, timeout: int):
        nonlocal attempts
        attempts += 1
        assert url == "http://127.0.0.1:8000"
        assert timeout == 1
        if attempts == 1:
            raise urllib.error.URLError("not ready")
        return _ReadyResponse()

    monkeypatch.setattr(local_app.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(local_app.webbrowser, "open", opened_urls.append)
    monkeypatch.setattr(local_app.time, "sleep", lambda _seconds: None)

    local_app._open_browser_when_ready(
        "http://127.0.0.1:8000",
        timeout_seconds=5,
        interval_seconds=0.01,
    )

    assert attempts == 2
    assert opened_urls == ["http://127.0.0.1:8000"]
