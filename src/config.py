"""Configuration management for the LM Anki Cards Creator application."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .llm_catalog import is_api_model_identifier, is_local_model_identifier
from .media_catalog import (
    IMAGE_PROVIDER_LOCAL,
    TTS_PROVIDER_QWEN3,
    get_default_image_model,
    get_default_tts_model,
    is_valid_image_model,
    is_valid_image_provider,
    is_valid_tts_model,
    is_valid_tts_provider,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=False)
load_dotenv(_PROJECT_ROOT / ".env.local", override=False)


@dataclass
class Config:
    """Central configuration class for the application."""

    # Model configuration
    model_path: str = "../models/gemma-2-2b-it-Q8_0.gguf"
    device: str = "auto"
    n_gpu_layers: int = -1
    n_ctx: int = 8192
    temperature: float = 0.0
    max_tokens: int = 2048

    # Audio configuration
    audio_format: str = "mp3"
    audio_language: str = "en"
    tts_provider: str = TTS_PROVIDER_QWEN3
    tts_model: str = ""
    qwen3_tts_model: str = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
    qwen3_tts_speaker: str = "Vivian"
    qwen3_tts_instruct: str = "Speak in a calm, clear voice."
    openai_tts_model: str = "openai/tts-1"
    google_tts_model: str = "gemini/gemini-2.5-flash-preview-tts"

    # Image generation configuration (Stable Diffusion 1.5 + LCM)
    enable_images: bool = True
    image_provider: str = IMAGE_PROVIDER_LOCAL
    image_model: str = ""
    openai_image_model: str = "gpt-image-1"
    google_image_model: str = "gemini/gemini-3.1-flash-image-preview"
    sd_model_file: str = "v1-5-pruned_Q4_0.gguf"
    sd_lcm_lora_name: str = "LCM_LoRA_Weights_SD15"
    sd_sample_steps: int = 8
    sd_cfg_scale: float = 2.0
    sd_image_width: int = 512
    sd_image_height: int = 512

    # API keys
    openai_api_key: str = ""

    # Paths
    data_dir: Path = Path("data")
    audio_dir: Path = Path("data/audio")
    json_dir: Path = Path("data/json files")
    anki_decks_dir: Path = Path("data/anki_decks")
    processed_expressions_dir: Path = Path("data/processed_expressions")
    cache_dir: Path = Path("data/cache")
    images_dir: Path = Path("data/images")
    models_dir: Path = Path(__file__).resolve().parent.parent / "models"

    # Processing settings
    enable_caching: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0

    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    def __post_init__(self) -> None:
        """Initialize configuration after dataclass creation."""
        # Auto-detect device if not specified
        if self.device == "auto":
            self.device = self._detect_device()

        # Create necessary directories
        self._create_directories()

    def _detect_device(self) -> str:
        """Auto-detect the best available device for model inference."""
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except Exception:
            pass
        return "cpu"

    def _create_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        directories = [
            self.data_dir,
            self.audio_dir,
            self.json_dir,
            self.anki_decks_dir,
            self.processed_expressions_dir,
            self.cache_dir,
            self.images_dir,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        config = cls()

        # Override with environment variables if present
        data_dir_env = os.getenv("DATA_DIR")
        if data_dir_env:
            data_dir = Path(data_dir_env)
            config.data_dir = data_dir
            config.audio_dir = data_dir / "audio"
            config.json_dir = data_dir / "json files"
            config.anki_decks_dir = data_dir / "anki_decks"
            config.processed_expressions_dir = data_dir / "processed_expressions"
            config.cache_dir = data_dir / "cache"
            config.images_dir = data_dir / "images"

        model_path_env = os.getenv("MODEL_PATH")
        if model_path_env:
            config.model_path = model_path_env
        device_env = os.getenv("DEVICE")
        if device_env:
            config.device = device_env
        audio_format_env = os.getenv("AUDIO_FORMAT")
        if audio_format_env:
            config.audio_format = audio_format_env
        log_level_env = os.getenv("LOG_LEVEL")
        if log_level_env:
            config.log_level = log_level_env
        openai_api_key_env = os.getenv("OPENAI_API_KEY")
        if openai_api_key_env:
            config.openai_api_key = openai_api_key_env
        tts_provider_env = os.getenv("TTS_PROVIDER")
        if tts_provider_env:
            config.tts_provider = tts_provider_env
        tts_model_env = os.getenv("TTS_MODEL")
        if tts_model_env:
            config.tts_model = tts_model_env
        image_provider_env = os.getenv("IMAGE_PROVIDER")
        if image_provider_env:
            config.image_provider = image_provider_env
        image_model_env = os.getenv("IMAGE_MODEL")
        if image_model_env:
            config.image_model = image_model_env
        models_dir_env = os.getenv("MODELS_DIR")
        if models_dir_env:
            config.models_dir = Path(models_dir_env)
        enable_images_env = os.getenv("ENABLE_IMAGES")
        if enable_images_env:
            config.enable_images = enable_images_env.lower() in (
                "1",
                "true",
                "yes",
                "on",
            )
        sd_model_file_env = os.getenv("SD_MODEL_FILE")
        if sd_model_file_env:
            config.sd_model_file = sd_model_file_env

        if not config.tts_model:
            config.tts_model = config.default_tts_model
        if not config.image_model:
            config.image_model = config.default_image_model

        config._create_directories()
        return config

    @property
    def sd_model_path(self) -> Path:
        """Full path to the Stable Diffusion GGUF model file."""
        return self.models_dir / self.sd_model_file

    @property
    def default_tts_model(self) -> str:
        """Return the configured default TTS model for the selected provider."""
        provider_defaults = {
            TTS_PROVIDER_QWEN3: self.qwen3_tts_model,
            "openai": self.openai_tts_model,
            "google": self.google_tts_model,
        }
        return provider_defaults.get(
            self.tts_provider, get_default_tts_model(self.tts_provider)
        )

    @property
    def default_image_model(self) -> str:
        """Return the configured default image model for the selected provider."""
        provider_defaults = {
            IMAGE_PROVIDER_LOCAL: "local/stable-diffusion",
            "openai": self.openai_image_model,
            "google": self.google_image_model,
        }
        return provider_defaults.get(
            self.image_provider,
            get_default_image_model(self.image_provider),
        )

    def validate(self) -> None:
        """Validate configuration settings."""
        if (
            is_local_model_identifier(self.model_path)
            and not Path(self.model_path).exists()
        ):
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        if not is_local_model_identifier(
            self.model_path
        ) and not is_api_model_identifier(self.model_path):
            raise ValueError(
                "MODEL_PATH must be a local .gguf path or a liteLLM identifier like 'openai/gpt-5.4-nano'."
            )

        if self.audio_format not in ["mp3", "wav"]:
            raise ValueError(f"Unsupported audio format: {self.audio_format}")

        if not is_valid_tts_provider(self.tts_provider):
            raise ValueError(f"Unsupported TTS provider: {self.tts_provider}")

        if not is_valid_tts_model(self.tts_provider, self.tts_model):
            raise ValueError(
                f"Unsupported TTS model '{self.tts_model}' for provider '{self.tts_provider}'"
            )

        if not is_valid_image_provider(self.image_provider):
            raise ValueError(f"Unsupported image provider: {self.image_provider}")

        if not is_valid_image_model(self.image_provider, self.image_model):
            raise ValueError(
                f"Unsupported image model '{self.image_model}' for provider '{self.image_provider}'"
            )

        if (
            self.enable_images
            and self.image_provider == IMAGE_PROVIDER_LOCAL
            and not self.sd_model_path.exists()
        ):
            raise FileNotFoundError(f"SD model file not found: {self.sd_model_path}")

        if self.device not in ["cpu", "cuda", "mps", "auto"]:
            raise ValueError(f"Unsupported device: {self.device}")


# Global configuration instance
config = Config.from_env()
