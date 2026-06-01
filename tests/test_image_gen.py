"""Tests for src/image_gen.py — local and liteLLM-backed image providers."""

import base64
from unittest.mock import MagicMock, patch

from src.image_gen import ImageGenerationService


def test_generate_image_openai_downloads_to_local_file(temp_dir):
    output_path = temp_dir / "openai.png"
    service = ImageGenerationService(provider="openai", model="gpt-image-1")

    fake_item = MagicMock()
    fake_item.url = "https://example.com/test.png"
    fake_response = MagicMock()
    fake_response.data = [fake_item]

    with (
        patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True),
        patch(
            "litellm.image_generation", return_value=fake_response
        ) as mock_image_generation,
        patch.object(
            service, "_download_image_bytes", return_value=b"png-bytes"
        ) as mock_download,
    ):
        result = service.generate_image("apple", "a fruit", output_path)

    assert output_path.read_bytes() == b"png-bytes"
    assert result == str(output_path)
    mock_image_generation.assert_called_once_with(
        model="gpt-image-1",
        prompt=mock_image_generation.call_args.kwargs["prompt"],
        n=1,
        size="1024x1024",
    )
    mock_download.assert_called_once_with("https://example.com/test.png")


def test_openai_image_size_normalizes_landscape_and_portrait():
    assert ImageGenerationService._openai_size(512, 512) == "1024x1024"
    assert ImageGenerationService._openai_size(1536, 1024) == "1536x1024"
    assert ImageGenerationService._openai_size(512, 900) == "1024x1536"
    assert ImageGenerationService._openai_size(900, 512) == "1536x1024"


def test_generate_image_google_decodes_data_url(temp_dir):
    output_path = temp_dir / "google.png"
    service = ImageGenerationService(
        provider="google",
        model="gemini/gemini-3.1-flash-image-preview",
    )

    image_bytes = b"fake-google-image"
    data_url = "data:image/png;base64," + base64.b64encode(image_bytes).decode("utf-8")
    fake_message = MagicMock()
    fake_message.images = [{"image_url": {"url": data_url}}]
    fake_choice = MagicMock()
    fake_choice.message = fake_message
    fake_response = MagicMock()
    fake_response.choices = [fake_choice]

    with (
        patch.dict("os.environ", {"GEMINI_API_KEY": "gem-test"}, clear=True),
        patch("litellm.completion", return_value=fake_response) as mock_completion,
    ):
        result = service.generate_image("apple", "a fruit", output_path)

    assert output_path.read_bytes() == image_bytes
    assert result == str(output_path)
    mock_completion.assert_called_once()
