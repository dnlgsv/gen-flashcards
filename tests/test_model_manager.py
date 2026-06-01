"""Tests for model_manager.py — JSON extraction, routing, and inference paths."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.exceptions import ModelInferenceError, ModelLoadError
from src.llm_catalog import normalize_model_name
from src.model_manager import ModelManager, _extract_json, _is_openai_model

# ---------------------------------------------------------------------------
# _is_openai_model
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,expected",
    [
        ("gpt-5.4-nano", True),
        ("/models/gemma-2-2b.gguf", False),
        ("llama-3.2", False),
        ("", False),
    ],
)
def test_is_openai_model(name, expected):
    assert _is_openai_model(name) is expected


# ---------------------------------------------------------------------------
# _extract_json
# ---------------------------------------------------------------------------


def test_extract_json_fenced():
    text = 'Here is the result:\n```json\n{"key": "value"}\n```'
    result = _extract_json(text)
    assert result == '{"key": "value"}'


def test_extract_json_unfenced_braces():
    text = 'Some preamble {"key": "value"} some suffix'
    result = _extract_json(text)
    assert result == '{"key": "value"}'


def test_extract_json_plain():
    text = '{"key": "value"}'
    result = _extract_json(text)
    assert result == '{"key": "value"}'


def test_extract_json_no_json():
    text = "No JSON here at all"
    result = _extract_json(text)
    assert result == text.strip()


# ---------------------------------------------------------------------------
# _parse_and_validate
# ---------------------------------------------------------------------------

VALID_JSON = json.dumps(
    {
        "original_form": "current",
        "part_of_speech": "adverb",
        "definition": "used to indicate something is happening currently",
        "examples": ["She is currently working.", "Currently, no data is available."],
        "synonyms": ["now", "at present"],
        "antonyms": [],
        "collocations": ["currently available", "currently working"],
        "translations": ["в настоящее время"],
        "cefr_level": "B1",
        "topics": ["time", "grammar"],
    }
)


def test_parse_and_validate_success():
    manager = ModelManager()
    result = manager._parse_and_validate(f"```json\n{VALID_JSON}\n```", "currently")
    assert result["expression"] == "currently"
    assert result["original_form"] == "current"
    assert result["part_of_speech"] == "adverb"
    assert isinstance(result["examples"], list)


def test_parse_and_validate_invalid_json():
    manager = ModelManager()
    with pytest.raises(ModelInferenceError, match="Failed to parse model response"):
        manager._parse_and_validate("not json at all", "word")


def test_parse_and_validate_filters_topics():
    """'language learning' topic should be stripped."""
    data = json.loads(VALID_JSON)
    data["topics"] = ["language learning", "grammar"]
    manager = ModelManager()
    result = manager._parse_and_validate(json.dumps(data), "currently")
    assert "language learning" not in result["topics"]
    assert "grammar" in result["topics"]


def test_parse_and_validate_coerces_string_to_list():
    """Schema coercion: synonyms as a bare string."""
    data = json.loads(VALID_JSON)
    data["synonyms"] = "now"
    manager = ModelManager()
    result = manager._parse_and_validate(json.dumps(data), "currently")
    assert result["synonyms"] == ["now"]


def test_parse_and_validate_sets_original_form_fallback():
    data = json.loads(VALID_JSON)
    data.pop("original_form", None)
    manager = ModelManager()
    result = manager._parse_and_validate(json.dumps(data), "currently")
    assert result["original_form"] == "currently"


# ---------------------------------------------------------------------------
# generate_card_info — OpenAI path (mocked)
# ---------------------------------------------------------------------------


def test_generate_card_info_openai_routes_correctly():
    manager = ModelManager()
    with patch.object(manager, "_generate_with_litellm") as mock_litellm:
        mock_litellm.return_value = {"expression": "test"}
        manager.generate_card_info("gpt-5.4-nano", "prompt", "test")
        mock_litellm.assert_called_once_with("openai/gpt-5.4-nano", "prompt", "test")


def test_generate_card_info_local_routes_correctly():
    manager = ModelManager()
    with patch.object(manager, "_generate_with_litellm") as mock_litellm:
        mock_litellm.return_value = {"expression": "test"}
        manager.generate_card_info("/models/gemma.gguf", "prompt", "test")
        mock_litellm.assert_called_once_with(
            "local-gguf//models/gemma.gguf", "prompt", "test"
        )


# ---------------------------------------------------------------------------
# liteLLM model normalization and inference
# ---------------------------------------------------------------------------


def test_normalize_model_name_preserves_litellm_identifiers():
    assert (
        normalize_model_name("anthropic/claude-sonnet-4-5")
        == "anthropic/claude-sonnet-4-5"
    )


def test_generate_with_litellm_success():
    manager = ModelManager()

    fake_message = MagicMock()
    fake_message.content = VALID_JSON
    fake_choice = MagicMock()
    fake_choice.message = fake_message
    fake_response = MagicMock()
    fake_response.choices = [fake_choice]

    with (
        patch("src.model_manager.config") as mock_config,
        patch("src.model_manager.ModelManager._ensure_local_provider_registered"),
        patch("litellm.completion") as mock_completion,
        patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True),
    ):
        mock_config.temperature = 0.0
        mock_config.max_tokens = 500
        mock_completion.return_value = fake_response

        result = manager._generate_with_litellm(
            "openai/gpt-5.4-nano", "prompt", "currently"
        )

    assert result["expression"] == "currently"
    assert result["part_of_speech"] == "adverb"


def test_generate_with_litellm_missing_openai_api_key():
    manager = ModelManager()
    with (
        patch.dict("os.environ", {}, clear=True),
        pytest.raises(ModelInferenceError, match="OPENAI_API_KEY"),
    ):
        manager._generate_with_litellm("openai/gpt-5.4-nano", "prompt", "word")


# ---------------------------------------------------------------------------
# get_model — singleton caching
# ---------------------------------------------------------------------------


def test_get_model_caches_instance():
    manager = ModelManager()
    manager._instances.clear()

    fake_model = MagicMock()
    with patch.object(
        manager, "_load_local_model", return_value=fake_model
    ) as mock_load:
        m1 = manager.get_model("/path/model.gguf")
        m2 = manager.get_model("/path/model.gguf")
        assert m1 is m2
        mock_load.assert_called_once()
    manager._instances.clear()


def test_get_model_load_error_raises():
    manager = ModelManager()
    manager._instances.clear()
    with (
        patch.object(manager, "_load_local_model", side_effect=Exception("disk error")),
        pytest.raises(ModelLoadError),
    ):
        manager.get_model("/bad/path.gguf")
    manager._instances.clear()
