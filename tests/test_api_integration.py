"""API integration tests for generation and deck routes."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.dependencies import get_config, get_task_store
from src.api.tasks import TaskStore
from src.config import Config


def _test_config(temp_dir: Path, **overrides) -> Config:
    values = {
        "model_path": "openai/gpt-5.4-nano",
        "enable_images": False,
        "data_dir": temp_dir / "data",
        "audio_dir": temp_dir / "data" / "audio",
        "json_dir": temp_dir / "data" / "json files",
        "anki_decks_dir": temp_dir / "data" / "anki_decks",
        "processed_expressions_dir": temp_dir / "data" / "processed_expressions",
        "cache_dir": temp_dir / "data" / "cache",
        "images_dir": temp_dir / "data" / "images",
    }
    values.update(overrides)
    return Config(**values)


def _client(
    temp_dir: Path,
    task_store: TaskStore | None = None,
    cfg: Config | None = None,
) -> TestClient:
    cfg = cfg or _test_config(temp_dir)
    store = task_store or TaskStore()
    app = create_app()
    app.dependency_overrides[get_config] = lambda: cfg
    app.dependency_overrides[get_task_store] = lambda: store
    return TestClient(app)


def test_start_generation_creates_task(temp_dir, monkeypatch):
    """POST /api/generate should create a task and expose completed status."""
    store = TaskStore()

    def fake_run_generation(task_id, request, task_store):
        assert request.learner_level == "B1"
        task_store.complete(task_id, [{"expression": request.words[0]}])

    monkeypatch.setattr("src.api.routers.generate.run_generation", fake_run_generation)

    with _client(temp_dir, store) as client:
        response = client.post(
            "/api/generate",
            json={
                "words": ["apple"],
                "model_name": "openai/gpt-5.4-nano",
                "learner_level": "B1",
                "enable_images": False,
            },
        )

        assert response.status_code == 202
        task_id = response.json()["task_id"]

        for _ in range(20):
            status = client.get(f"/api/generate/{task_id}").json()
            if status["status"] == "completed":
                break
            time.sleep(0.01)

        assert status["status"] == "completed"
        assert status["result"] == [{"expression": "apple"}]


def test_start_generation_rejects_invalid_model(temp_dir):
    """POST /api/generate should reject malformed model identifiers."""
    with _client(temp_dir) as client:
        response = client.post(
            "/api/generate",
            json={
                "words": ["apple"],
                "model_name": "not-a-model",
                "enable_images": False,
            },
        )

    assert response.status_code == 400
    assert "model_name must be" in response.json()["detail"]


def test_start_generation_rejects_empty_words(temp_dir):
    """POST /api/generate should reject empty word lists after trimming."""
    with _client(temp_dir) as client:
        response = client.post(
            "/api/generate",
            json={
                "words": ["   "],
                "model_name": "openai/gpt-5.4-nano",
                "enable_images": False,
            },
        )

    assert response.status_code == 422


def test_extract_candidates_returns_limited_shortlist_without_model(temp_dir):
    """POST /api/candidates/extract should work without model credentials."""
    text = (
        "Machine learning systems need clean data. "
        "Machine learning workflows need careful evaluation. "
        "Language learners benefit from targeted vocabulary practice."
    )
    with _client(temp_dir) as client:
        response = client.post(
            "/api/candidates/extract",
            json={
                "text": text,
                "language": "en",
                "learner_level": "B1",
                "target_count": 5,
                "include_phrases": True,
                "use_model_rerank": False,
            },
        )

    assert response.status_code == 200
    candidates = response.json()["candidates"]
    assert 0 < len(candidates) <= 5
    assert any(
        candidate["expression"] == "machine learning" for candidate in candidates
    )


def test_extract_candidates_rejects_empty_text(temp_dir):
    """POST /api/candidates/extract should reject empty source text."""
    with _client(temp_dir) as client:
        response = client.post(
            "/api/candidates/extract",
            json={"text": " ", "target_count": 10, "use_model_rerank": False},
        )

    assert response.status_code == 422


def test_build_deck_and_download(temp_dir):
    """POST /api/deck/build should create a downloadable APKG file."""
    with _client(temp_dir) as client:
        response = client.post(
            "/api/deck/build",
            json={
                "deck_name": "Integration Deck",
                "cards_data": [
                    {
                        "expression": "apple",
                        "definition": "a fruit",
                        "examples": ["I ate an apple."],
                    }
                ],
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["deck_name"] == "Integration Deck"
        assert body["card_count"] == 1
        assert body["download_url"].startswith("/api/deck/deck_")

        download = client.get(body["download_url"])

    assert download.status_code == 200
    assert download.content


def test_import_deck_reads_apkg_cards(temp_dir):
    """POST /api/deck/import should read cards from an APKG file."""
    with _client(temp_dir) as client:
        build = client.post(
            "/api/deck/build",
            json={
                "deck_name": "Imported Deck",
                "cards_data": [
                    {
                        "expression": "apple",
                        "original_form": "apple",
                        "definition": "a fruit",
                        "examples": ["I ate an apple."],
                        "synonyms": ["pome"],
                        "translations": ["яблоко"],
                    }
                ],
            },
        )
        deck_bytes = client.get(build.json()["download_url"]).content

        response = client.post(
            "/api/deck/import?filename=imported.apkg",
            content=deck_bytes,
            headers={"Content-Type": "application/octet-stream"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["deck_name"] == "Imported Deck"
    assert body["card_count"] == 1
    assert body["cards"][0]["expression"] == "apple"
    assert body["cards"][0]["definition"] == "a fruit"
    assert body["cards"][0]["examples"] == ["I ate an apple."]
    assert body["cards"][0]["translations"] == ["яблоко"]


def test_build_deck_rejects_duplicate_expressions(temp_dir):
    """POST /api/deck/build should reject duplicate card expressions."""
    with _client(temp_dir) as client:
        response = client.post(
            "/api/deck/build",
            json={
                "deck_name": "Duplicate Deck",
                "cards_data": [
                    {"expression": "apple", "definition": "a fruit"},
                    {"expression": "Apple", "definition": "same fruit"},
                ],
            },
        )

    assert response.status_code == 422
    assert "duplicate card expression" in str(response.json()["detail"])


def test_preflight_reports_ready_for_valid_cloud_config(temp_dir, monkeypatch):
    """GET /api/preflight should report ready for a valid cloud-model setup."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    with _client(temp_dir) as client:
        response = client.get("/api/preflight")

    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert {check["name"] for check in body["checks"]} == {
        "model",
        "tts",
        "images",
        "runtime_dirs",
    }


def test_preflight_reports_missing_local_image_model(temp_dir, monkeypatch):
    """GET /api/preflight should surface missing local image model files."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    cfg = _test_config(
        temp_dir,
        enable_images=True,
        image_provider="local",
        models_dir=temp_dir / "missing_models",
    )

    with _client(temp_dir, cfg=cfg) as client:
        response = client.get("/api/preflight")

    assert response.status_code == 200
    body = response.json()
    image_check = next(check for check in body["checks"] if check["name"] == "images")
    assert body["ready"] is False
    assert image_check["status"] == "error"
    assert "Stable Diffusion model file not found" in image_check["message"]
