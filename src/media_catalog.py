"""Shared media provider catalogs for image generation and TTS."""

from __future__ import annotations

from dataclasses import dataclass

IMAGE_PROVIDER_LOCAL = "local"
IMAGE_PROVIDER_OPENAI = "openai"
IMAGE_PROVIDER_GOOGLE = "google"

TTS_PROVIDER_QWEN3 = "qwen3"
TTS_PROVIDER_OPENAI = "openai"
TTS_PROVIDER_GOOGLE = "google"


@dataclass(frozen=True)
class MediaOption:
    """A selectable provider model or voice option."""

    value: str
    label: str


IMAGE_PROVIDER_OPTIONS: tuple[MediaOption, ...] = (
    MediaOption(IMAGE_PROVIDER_LOCAL, "Local Stable Diffusion"),
    MediaOption(IMAGE_PROVIDER_OPENAI, "OpenAI Image API"),
    MediaOption(IMAGE_PROVIDER_GOOGLE, "Google Nano Banana 2"),
)

TTS_PROVIDER_OPTIONS: tuple[MediaOption, ...] = (
    MediaOption(TTS_PROVIDER_QWEN3, "Local Qwen3 TTS"),
    MediaOption(TTS_PROVIDER_OPENAI, "OpenAI TTS"),
    MediaOption(TTS_PROVIDER_GOOGLE, "Google Gemini TTS"),
)

IMAGE_MODEL_OPTIONS: dict[str, tuple[MediaOption, ...]] = {
    IMAGE_PROVIDER_LOCAL: (
        MediaOption("local/stable-diffusion", "Stable Diffusion 1.5 + LCM"),
    ),
    IMAGE_PROVIDER_OPENAI: (
        MediaOption("gpt-image-1", "GPT Image 1"),
        MediaOption("dall-e-3", "DALL-E 3"),
    ),
    IMAGE_PROVIDER_GOOGLE: (
        MediaOption(
            "gemini/gemini-3.1-flash-image-preview",
            "Nano Banana 2 (Gemini 3.1 Flash Image)",
        ),
    ),
}

TTS_MODEL_OPTIONS: dict[str, tuple[MediaOption, ...]] = {
    TTS_PROVIDER_QWEN3: (
        MediaOption(
            "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
            "Qwen3 TTS Custom Voice",
        ),
    ),
    TTS_PROVIDER_OPENAI: (
        MediaOption("openai/tts-1", "TTS 1"),
        MediaOption("openai/tts-1-hd", "TTS 1 HD"),
        MediaOption("openai/gpt-4o-mini-tts", "GPT-4o mini TTS"),
    ),
    TTS_PROVIDER_GOOGLE: (
        MediaOption("gemini/gemini-2.5-flash-preview-tts", "Gemini 2.5 Flash TTS"),
        MediaOption("gemini/gemini-2.5-pro-preview-tts", "Gemini 2.5 Pro TTS"),
    ),
}

TTS_VOICE_OPTIONS: dict[str, tuple[MediaOption, ...]] = {
    TTS_PROVIDER_QWEN3: (
        MediaOption("Vivian", "Vivian"),
        MediaOption("Ryan", "Ryan"),
    ),
    TTS_PROVIDER_OPENAI: (
        MediaOption("alloy", "alloy"),
        MediaOption("echo", "echo"),
        MediaOption("fable", "fable"),
        MediaOption("onyx", "onyx"),
        MediaOption("nova", "nova"),
        MediaOption("shimmer", "shimmer"),
    ),
    TTS_PROVIDER_GOOGLE: (
        MediaOption("Kore", "Kore"),
        MediaOption("Puck", "Puck"),
        MediaOption("Charon", "Charon"),
    ),
}


def get_image_provider_options() -> list[MediaOption]:
    return list(IMAGE_PROVIDER_OPTIONS)


def get_tts_provider_options() -> list[MediaOption]:
    return list(TTS_PROVIDER_OPTIONS)


def get_image_model_options(provider: str) -> list[MediaOption]:
    return list(IMAGE_MODEL_OPTIONS.get(provider, ()))


def get_tts_model_options(provider: str) -> list[MediaOption]:
    return list(TTS_MODEL_OPTIONS.get(provider, ()))


def get_tts_voice_options(provider: str) -> list[MediaOption]:
    return list(TTS_VOICE_OPTIONS.get(provider, ()))


def get_default_image_model(provider: str) -> str:
    options = get_image_model_options(provider)
    return options[0].value if options else ""


def get_default_tts_model(provider: str) -> str:
    options = get_tts_model_options(provider)
    return options[0].value if options else ""


def get_default_tts_voice(provider: str) -> str:
    options = get_tts_voice_options(provider)
    return options[0].value if options else ""


def is_valid_image_model(provider: str, model: str | None) -> bool:
    if not model:
        return True
    return model in {option.value for option in IMAGE_MODEL_OPTIONS.get(provider, ())}


def is_valid_tts_model(provider: str, model: str | None) -> bool:
    if not model:
        return True
    return model in {option.value for option in TTS_MODEL_OPTIONS.get(provider, ())}


def is_valid_tts_voice(provider: str, voice: str | None) -> bool:
    if not voice:
        return True
    return voice in {option.value for option in TTS_VOICE_OPTIONS.get(provider, ())}


def is_valid_image_provider(provider: str) -> bool:
    return provider in {option.value for option in IMAGE_PROVIDER_OPTIONS}


def is_valid_tts_provider(provider: str) -> bool:
    return provider in {option.value for option in TTS_PROVIDER_OPTIONS}
