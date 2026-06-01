"""Image generation service for Anki flashcards using Stable Diffusion 1.5 + LCM LoRA."""

from __future__ import annotations

import base64
import os
import re
import threading
from pathlib import Path

from .config import config
from .exceptions import ImageGenerationError
from .logger import LoggerMixin
from .media_catalog import (
    IMAGE_PROVIDER_GOOGLE,
    IMAGE_PROVIDER_LOCAL,
    IMAGE_PROVIDER_OPENAI,
    get_default_image_model,
)

try:
    from stable_diffusion_cpp import StableDiffusion

    SD_CPP_AVAILABLE = True
except Exception:
    SD_CPP_AVAILABLE = False


class ImageGenerationService(LoggerMixin):
    """Generate illustrative images for vocabulary flashcards using SD 1.5 with LCM acceleration."""

    _load_lock: threading.Lock = threading.Lock()

    def __init__(self, provider: str | None = None, model: str | None = None) -> None:
        self.provider = provider or config.image_provider
        self.model_name = (
            model or config.image_model or get_default_image_model(self.provider)
        )
        self._model: StableDiffusion | None = None

    def _load_model(self) -> StableDiffusion:
        """Lazily load the SD model (thread-safe)."""
        if self._model is not None:
            return self._model

        if not SD_CPP_AVAILABLE:
            raise ImageGenerationError(
                "stable-diffusion-cpp-python is not installed. "
                "Install it with: pip install stable-diffusion-cpp-python"
            )

        with self._load_lock:
            if self._model is not None:
                return self._model

            model_path = config.sd_model_path
            if not model_path.exists():
                raise ImageGenerationError(f"SD model file not found: {model_path}")

            lora_dir = str(model_path.parent)

            self.logger.info(f"Loading SD 1.5 model from {model_path}")
            self._model = StableDiffusion(
                model_path=str(model_path),
                lora_model_dir=lora_dir,
                vae_decode_only=True,
                n_threads=os.cpu_count() or 4,
                keep_clip_on_cpu=True,
                verbose=False,
            )
            self.logger.info("SD 1.5 model loaded")

        return self._model

    def _build_prompt(self, expression: str, definition: str) -> str:
        """Build an image prompt from the card's expression and definition."""
        base = (
            f"minimalist illustration of {expression}, {definition}, "
            "simple shapes, flat colors, white background, clean lines, "
            "modern minimal design, bold silhouette, no gradients, no shadows"
        )
        # Append LCM LoRA trigger
        lora_name = config.sd_lcm_lora_name
        if lora_name:
            base += f" <lora:{lora_name}:1.0>"
        return base

    def generate_image(
        self,
        expression: str,
        definition: str,
        output_path: str | Path,
        *,
        width: int = 512,
        height: int = 512,
        seed: int = -1,
    ) -> str:
        """Generate an illustration for a vocabulary card.

        Args:
            expression: The word or phrase.
            definition: Its definition (used to guide the image).
            output_path: Where to save the PNG file.
            width: Image width in pixels.
            height: Image height in pixels.
            seed: Random seed (-1 for random).

        Returns:
            The path to the saved image file, or empty string on failure.
        """
        output_path = Path(output_path)

        if output_path.exists():
            self.logger.debug(f"Image already exists: {output_path}")
            return str(output_path)

        try:
            prompt = self._build_prompt(expression, definition)
            self.logger.info(
                "Generating image for '%s' with provider=%s model=%s",
                expression,
                self.provider,
                self.model_name,
            )

            if self.provider == IMAGE_PROVIDER_LOCAL:
                return self._generate_local(prompt, output_path, width, height, seed)
            if self.provider == IMAGE_PROVIDER_OPENAI:
                return self._generate_openai(prompt, output_path, width, height)
            if self.provider == IMAGE_PROVIDER_GOOGLE:
                return self._generate_google(prompt, output_path)
            raise ImageGenerationError(f"Unsupported image provider: {self.provider}")

        except ImageGenerationError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to generate image for '{expression}': {e}")
            raise ImageGenerationError(f"Image generation failed: {e}") from e

    def _generate_local(
        self,
        prompt: str,
        output_path: Path,
        width: int,
        height: int,
        seed: int,
    ) -> str:
        model = self._load_model()
        negative = (
            "blurry, low quality, deformed, ugly, noisy, grainy, "
            "dark background, black background, gray background, "
            "photorealistic, photo, 3d render, realistic, hyperrealistic, "
            "watermark, text, letters, words, signature"
        )

        results = model.generate_image(
            prompt=prompt,
            negative_prompt=negative,
            sample_method="lcm",
            sample_steps=config.sd_sample_steps,
            cfg_scale=config.sd_cfg_scale,
            width=width,
            height=height,
            seed=seed,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        results[0].save(str(output_path))
        self.logger.info(f"Image saved: {output_path}")
        return str(output_path)

    @staticmethod
    def _extract_data_url(value: str) -> bytes:
        match = re.match(r"^data:[^;]+;base64,(?P<data>.+)$", value)
        if not match:
            raise ImageGenerationError("Expected base64 data URL for image generation")
        return base64.b64decode(match.group("data"))

    @staticmethod
    def _write_image_bytes(output_path: Path, image_bytes: bytes) -> str:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        return str(output_path)

    @staticmethod
    def _download_image_bytes(url: str) -> bytes:
        import requests

        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.content

    @staticmethod
    def _openai_size(width: int, height: int) -> str:
        supported_sizes = {
            (1024, 1024): "1024x1024",
            (1024, 1536): "1024x1536",
            (1536, 1024): "1536x1024",
        }
        if (width, height) in supported_sizes:
            return supported_sizes[(width, height)]
        if width > height:
            return "1536x1024"
        if height > width:
            return "1024x1536"
        return "1024x1024"

    def _write_image_from_value(self, output_path: Path, value: str) -> str:
        if value.startswith("data:image"):
            return self._write_image_bytes(output_path, self._extract_data_url(value))

        return self._write_image_bytes(output_path, self._download_image_bytes(value))

    def _generate_openai(
        self, prompt: str, output_path: Path, width: int, height: int
    ) -> str:
        if not os.getenv("OPENAI_API_KEY"):
            raise ImageGenerationError(
                "OPENAI_API_KEY is not set. Add it to your .env file."
            )

        from litellm import image_generation

        response = image_generation(
            model=self.model_name or get_default_image_model(IMAGE_PROVIDER_OPENAI),
            prompt=prompt,
            n=1,
            size=self._openai_size(width, height),
        )
        item = response.data[0]
        image_url = getattr(item, "url", None) or item.get("url")
        b64_json = getattr(item, "b64_json", None) or item.get("b64_json")
        if image_url:
            return self._write_image_from_value(output_path, image_url)
        if b64_json:
            return self._write_image_bytes(output_path, base64.b64decode(b64_json))
        raise ImageGenerationError("OpenAI image generation returned no image payload")

    def _generate_google(self, prompt: str, output_path: Path) -> str:
        if not os.getenv("GEMINI_API_KEY"):
            raise ImageGenerationError(
                "GEMINI_API_KEY is not set. Add it to your .env file."
            )

        from litellm import completion

        response = completion(
            model=self.model_name or get_default_image_model(IMAGE_PROVIDER_GOOGLE),
            messages=[{"role": "user", "content": prompt}],
            modalities=["image", "text"],
        )

        message = response.choices[0].message
        images = getattr(message, "images", None) or []
        if images:
            image_url = images[0]["image_url"]["url"]
            return self._write_image_from_value(output_path, image_url)

        content = getattr(message, "content", None) or ""
        if isinstance(content, str) and content.startswith("data:image"):
            return self._write_image_from_value(output_path, content)

        raise ImageGenerationError("Google image generation returned no image payload")
