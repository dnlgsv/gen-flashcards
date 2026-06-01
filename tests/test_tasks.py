"""Tests for background generation task behavior."""

from src.api.schemas import GenerateRequest, TaskStatusEnum
from src.api.tasks import TaskStore, run_generation


def test_run_generation_counts_failed_words_as_processed(monkeypatch):
    """Partial failures should still advance task progress accounting."""

    class FakeGenerator:
        def __init__(self, **kwargs):
            pass

        def get_expression_card_info(self, model_name, prompt, word):
            if word == "bad":
                raise RuntimeError("no card")
            return {"expression": word}

        def _generate_audio_files(self, card_data, word, audio_format):
            return card_data

        def _generate_image(self, card_data, word):
            return card_data

        def _save_card_data(self, card_data, word):
            return None

    monkeypatch.setattr("src.main.AnkiCardsGenerator", FakeGenerator)
    monkeypatch.setattr("src.main.load_prompt", lambda: "prompt")

    store = TaskStore()
    task_id = "task-1"
    store.create(task_id, total_words=2)
    request = GenerateRequest(
        words=["good", "bad"],
        model_name="openai/gpt-5.4-nano",
        enable_images=False,
    )

    run_generation(task_id, request, store)

    task = store.get(task_id)
    assert task is not None
    assert task.status == TaskStatusEnum.completed
    assert task.processed_words == 2
    assert task.result == [{"expression": "good"}]
    assert [event.event_type for event in task.events].count("word_error") == 1
    assert task.events[-1].event_type == "complete"
    assert task.events[-1].data["skipped"] == 1


def test_run_generation_adds_learner_level_to_prompt(monkeypatch):
    """Selected learner level should guide model prompt generation."""
    seen_prompts: list[str] = []

    class FakeGenerator:
        def __init__(self, **kwargs):
            pass

        def get_expression_card_info(self, model_name, prompt, word):
            seen_prompts.append(prompt)
            return {"expression": word}

        def _generate_audio_files(self, card_data, word, audio_format):
            return card_data

        def _generate_image(self, card_data, word):
            return card_data

        def _save_card_data(self, card_data, word):
            return None

    monkeypatch.setattr("src.main.AnkiCardsGenerator", FakeGenerator)
    monkeypatch.setattr("src.main.load_prompt", lambda: "base prompt")

    store = TaskStore()
    task_id = "task-2"
    store.create(task_id, total_words=1)
    request = GenerateRequest(
        words=["apple"],
        model_name="openai/gpt-5.4-nano",
        learner_level="A2",
        enable_images=False,
    )

    run_generation(task_id, request, store)

    assert seen_prompts
    assert "Target learner level: A2" in seen_prompts[0]
    assert "definitions understandable" in seen_prompts[0]


def test_run_generation_skips_audio_when_disabled(monkeypatch):
    """enable_audio=False should skip TTS file generation."""
    audio_calls = 0

    class FakeGenerator:
        def __init__(self, **kwargs):
            pass

        def get_expression_card_info(self, model_name, prompt, word):
            return {"expression": word}

        def _generate_audio_files(self, card_data, word, audio_format):
            nonlocal audio_calls
            audio_calls += 1
            return card_data

        def _generate_image(self, card_data, word):
            return card_data

        def _save_card_data(self, card_data, word):
            return None

    monkeypatch.setattr("src.main.AnkiCardsGenerator", FakeGenerator)
    monkeypatch.setattr("src.main.load_prompt", lambda: "prompt")

    store = TaskStore()
    task_id = "task-4"
    store.create(task_id, total_words=1)
    request = GenerateRequest(
        words=["apple"],
        model_name="openai/gpt-5.4-nano",
        enable_audio=False,
        enable_images=False,
    )

    run_generation(task_id, request, store)

    task = store.get(task_id)
    assert task is not None
    assert task.status == TaskStatusEnum.completed
    assert audio_calls == 0
