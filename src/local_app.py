"""Local browser app entry point."""

from __future__ import annotations

import socket
import threading
import time
import urllib.error
import urllib.request
import webbrowser


def _find_free_port(preferred_port: int = 8000) -> int:
    """Return preferred_port when available, otherwise ask the OS for a free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(("127.0.0.1", preferred_port)) != 0:
            return preferred_port

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _open_browser_when_ready(
    url: str,
    *,
    timeout_seconds: float = 30.0,
    interval_seconds: float = 0.25,
) -> None:
    """Open url after the local server starts returning HTTP responses."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status < 500:
                    webbrowser.open(url)
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(interval_seconds)

    print(f"Server did not become ready in {timeout_seconds:g}s. Open manually: {url}")


def main() -> None:
    """Run the local FastAPI app and open it in the default browser."""
    import uvicorn  # noqa: PLC0415

    port = _find_free_port()
    url = f"http://127.0.0.1:{port}"
    if port != 8000:
        print(f"Port 8000 is busy. Starting Anki Cards on {url}")
    else:
        print(f"Starting Anki Cards on {url}")
    threading.Thread(target=_open_browser_when_ready, args=(url,), daemon=True).start()
    uvicorn.run(
        "src.api.run:app",
        host="127.0.0.1",
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
