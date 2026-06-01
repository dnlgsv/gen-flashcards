"""Text-to-Speech service for the LM Anki Cards Creator application."""

import os
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

try:
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    QWEN3_TTS_AVAILABLE = True
except Exception:
    QWEN3_TTS_AVAILABLE = False

from .config import config
from .exceptions import AudioGenerationError
from .logger import LoggerMixin
from .media_catalog import (
    TTS_PROVIDER_GOOGLE,
    TTS_PROVIDER_OPENAI,
    TTS_PROVIDER_QWEN3,
    get_default_tts_model,
    get_default_tts_voice,
)

load_dotenv()

# Map ISO-639-1 language codes to Qwen3-TTS language names
_QWEN3_LANGUAGE_MAP: dict[str, str] = {
    "en": "English",
    "ru": "Russian",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "ja": "Japanese",
    "zh": "Chinese",
    "ko": "Korean",
    "pt": "Portuguese",
    "ar": "Arabic",
    "nl": "Dutch",
    "pl": "Polish",
    "tr": "Turkish",
}


class TextToSpeechService(LoggerMixin):
    """Text-to-speech service using Qwen3 TTS.

    Supports both string and list-of-strings input and skips regeneration when
    the output file already exists.
    """

    # Shared lock ensures only one thread loads the Qwen3 model at a time,
    # preventing the "Cannot copy out of meta tensor" error that arises when
    # multiple threads call from_pretrained() concurrently.
    _qwen3_load_lock: threading.Lock = threading.Lock()

    def __init__(
        self,
        provider: str | None = None,
        language: str | None = None,
        speaker: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialise the TTS service.

        Args:
            provider: TTS backend to use – only "qwen3" is supported.
                      Defaults to ``config.tts_provider``.
            language: ISO-639-1 language code (e.g. "en", "ru").
                      Defaults to ``config.audio_language``.
            speaker: Qwen3 TTS speaker name – "Vivian" (female) or "Ryan" (male).
                     Defaults to ``config.qwen3_tts_speaker``.
        """
        self.provider = provider or config.tts_provider
        self.language = language or config.audio_language
        self.model_name = model or config.tts_model or self._default_model()
        self.speaker = speaker or self._default_voice()
        self._qwen3_model = None  # lazy-loaded

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_audio_dir(self, filename: str) -> None:
        """Ensure the directory for the audio file exists."""
        Path(filename).parent.mkdir(parents=True, exist_ok=True)

    def _prepare_text(self, text: str | list[str]) -> str:
        """Prepare text for TTS processing.

        Args:
            text: Input text (string or list of strings)

        Returns:
            Processed text string ready for TTS
        """
        if isinstance(text, list):
            return " ".join(str(item) for item in text if item)
        return str(text) if text else ""

    def _load_qwen3_model(self):
        """Lazily load the Qwen3 TTS model (thread-safe)."""
        if self._qwen3_model is not None:
            return self._qwen3_model

        if not QWEN3_TTS_AVAILABLE:
            raise AudioGenerationError(
                "Qwen3 TTS dependencies are not available. "
                "Install them with: pip install qwen-tts soundfile torch"
            )

        with TextToSpeechService._qwen3_load_lock:
            # Second check inside the lock – another thread may have loaded
            # the model while this thread was waiting to acquire the lock.
            if self._qwen3_model is not None:
                return self._qwen3_model

            device = "cuda:0" if torch.cuda.is_available() else "cpu"
            dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
            resolved_model = self.model_name or config.qwen3_tts_model
            self.logger.info(f"Loading Qwen3 TTS model '{resolved_model}' on {device}")

            self._qwen3_model = Qwen3TTSModel.from_pretrained(
                resolved_model,
                device_map=device,
                dtype=dtype,
                attn_implementation="sdpa",
            )
            self.logger.info("Qwen3 TTS model loaded")

        return self._qwen3_model

    def _qwen3_language(self) -> str:
        """Return the Qwen3 language name for the configured language."""
        lang_code = self.language.lower().split("-")[0]
        language = _QWEN3_LANGUAGE_MAP.get(lang_code)
        if language is None:
            self.logger.warning(
                f"Unsupported language code '{lang_code}' for Qwen3 TTS. Falling back to 'English'."
            )
            language = "English"
        return language

    def _wav_filename(self, filename: str) -> str:
        """Return *filename* with its extension replaced by .wav."""
        return str(Path(filename).with_suffix(".wav"))

    def _default_model(self) -> str:
        provider_defaults = {
            TTS_PROVIDER_QWEN3: config.qwen3_tts_model,
            TTS_PROVIDER_OPENAI: config.openai_tts_model,
            TTS_PROVIDER_GOOGLE: config.google_tts_model,
        }
        return provider_defaults.get(
            self.provider, get_default_tts_model(self.provider)
        )

    def _default_voice(self) -> str:
        provider_defaults = {
            TTS_PROVIDER_QWEN3: config.qwen3_tts_speaker,
            TTS_PROVIDER_OPENAI: "alloy",
            TTS_PROVIDER_GOOGLE: "Kore",
        }
        return provider_defaults.get(
            self.provider, get_default_tts_voice(self.provider)
        )

    def _litellm_filename(self, filename: str) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix in {".mp3", ".wav"}:
            return filename
        return str(Path(filename).with_suffix(".mp3"))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_audio(self, text: str | list[str], filename: str) -> str:
        """Convert text to speech and save as a WAV audio file.

        The output is always a WAV file – the returned filename will have a
        ``.wav`` extension regardless of what was passed in.

        Args:
            text: Text to convert (string or list of strings)
            filename: Desired output filename for the audio file

        Returns:
            Filename of the generated audio file, empty string on failure

        Raises:
            AudioGenerationError: If audio generation fails
        """
        try:
            if self.provider == TTS_PROVIDER_QWEN3:
                filename = self._wav_filename(filename)
            else:
                filename = self._litellm_filename(filename)

            if os.path.exists(filename):
                self.logger.debug(f"Audio file already exists: {filename}")
                return filename

            processed_text = self._prepare_text(text)
            if not processed_text:
                self.logger.warning("Empty text provided for TTS")
                return ""

            self._ensure_audio_dir(filename)

            if self.provider == TTS_PROVIDER_QWEN3:
                return self._generate_qwen3(processed_text, filename)
            if self.provider == TTS_PROVIDER_OPENAI:
                return self._generate_openai(processed_text, filename)
            if self.provider == TTS_PROVIDER_GOOGLE:
                return self._generate_google(processed_text, filename)
            raise AudioGenerationError(f"Unsupported TTS provider: {self.provider}")

        except AudioGenerationError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to generate audio for '{filename}': {e}")
            raise AudioGenerationError(f"TTS generation failed: {e}") from e

    # ------------------------------------------------------------------
    # Backend implementation
    # ------------------------------------------------------------------

    def _generate_qwen3(self, text: str, filename: str) -> str:
        """Generate audio using Qwen3 TTS."""
        model = self._load_qwen3_model()
        language = self._qwen3_language()

        max_retries = config.max_retries
        for attempt in range(max_retries):
            try:
                wavs, sr = model.generate_custom_voice(
                    text=text,
                    language=language,
                    speaker=self.speaker,
                    instruct=config.qwen3_tts_instruct,
                )
                sf.write(filename, wavs[0], sr)
                self.logger.info(f"Generated audio with Qwen3 TTS: {filename}")
                return filename
            except Exception as e:
                if attempt == max_retries - 1:
                    raise AudioGenerationError(
                        f"Qwen3 TTS generation failed: {e}"
                    ) from e
                self.logger.warning(
                    f"Qwen3 TTS attempt {attempt + 1} failed: {e}, retrying..."
                )
                time.sleep(config.retry_delay)

        return ""  # unreachable, but satisfies type checker

    def _generate_openai(self, text: str, filename: str) -> str:
        if not os.getenv("OPENAI_API_KEY"):
            raise AudioGenerationError(
                "OPENAI_API_KEY is not set. Add it to your .env file."
            )

        from litellm import speech

        response = speech(
            model=self.model_name or config.openai_tts_model,
            voice=self.speaker,
            input=text,
            response_format=Path(filename).suffix.lstrip(".") or "mp3",
        )
        response.stream_to_file(filename)
        self.logger.info(f"Generated audio with OpenAI TTS: {filename}")
        return filename

    def _generate_google(self, text: str, filename: str) -> str:
        if not os.getenv("GEMINI_API_KEY"):
            raise AudioGenerationError(
                "GEMINI_API_KEY is not set. Add it to your .env file."
            )

        from litellm import speech

        response = speech(
            model=self.model_name or config.google_tts_model,
            voice=self.speaker,
            input=text,
            api_key=os.getenv("GEMINI_API_KEY"),
        )
        response.stream_to_file(filename)
        self.logger.info(f"Generated audio with Gemini TTS: {filename}")
        return filename
