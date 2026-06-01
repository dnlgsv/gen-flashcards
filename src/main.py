"""Module: Anki Cards Creator.

This module generates Anki flashcards for a list of vocabulary words using a language model
to derive card details and a text-to-speech service to create corresponding audio files.
It produces JSON files with card data and an Anki package that includes audio references.
"""

import argparse
import json
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from importlib.resources import files
from pathlib import Path

import genanki

from .anki_utils import create_anki_deck, referenced_media_files
from .cache import cache_manager
from .config import config
from .exceptions import FileProcessingError, ImageGenerationError, ModelError
from .image_gen import ImageGenerationService
from .logger import LoggerMixin, get_logger
from .media_catalog import (
    IMAGE_PROVIDER_GOOGLE,
    IMAGE_PROVIDER_LOCAL,
    IMAGE_PROVIDER_OPENAI,
    TTS_PROVIDER_GOOGLE,
    TTS_PROVIDER_OPENAI,
    TTS_PROVIDER_QWEN3,
    get_default_image_model,
    get_default_tts_model,
)
from .model_manager import model_manager
from .nlp_utils import parse_words
from .tts import TextToSpeechService


def load_prompt() -> str:
    """Load the prompt from the JSON file."""
    prompt_path = files("src").joinpath("prompts", "prompt.json")
    with prompt_path.open(encoding="utf-8") as f:
        prompt_data = json.load(f)
    if isinstance(prompt_data, str):
        return prompt_data
    return prompt_data.get("user", "")


def prompt_with_learner_level(prompt: str, learner_level: str = "auto") -> str:
    """Add learner-level guidance to the model prompt."""
    level = learner_level.strip().upper()
    if level == "AUTO" or level not in {"A1", "A2", "B1", "B2", "C1", "C2"}:
        return prompt

    return (
        f"{prompt}\n\n"
        "Learner adaptation:\n"
        f"- Target learner level: {level}.\n"
        "- Keep definitions understandable for this level.\n"
        "- Make example sentences natural and no harder than this level unless the target word requires it.\n"
        "- Prefer common vocabulary and short sentence structure for A1-B1 learners.\n"
    )


class AnkiCardsGenerator(LoggerMixin):
    """Main class for generating Anki cards from vocabulary words."""

    # Map ISO-639-1 code → human-readable language name used in the prompt
    _LANGUAGE_NAMES: dict[str, str] = {
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

    def __init__(
        self,
        tts_provider: str | None = None,
        tts_model: str | None = None,
        language: str | None = None,
        speaker: str | None = None,
        target_language: str | None = None,
        enable_images: bool | None = None,
        image_provider: str | None = None,
        image_model: str | None = None,
    ):
        """Initialize the Anki cards generator.

        Args:
            tts_provider: TTS backend – qwen3, openai, or google.
                          Defaults to ``config.tts_provider``.
            tts_model: Provider-specific TTS model identifier.
            language: ISO-639-1 language code for audio generation (e.g. "en", "ru").
                      Defaults to ``config.audio_language``.
            speaker: Provider-specific voice / speaker value.
            target_language: ISO-639-1 code for the translation target language.
                             Defaults to "ru" (Russian).
            enable_images: Whether to generate illustrative images for cards.
                           Defaults to ``config.enable_images``.
            image_provider: Image backend – local, openai, or google.
            image_model: Provider-specific image model identifier.
        """
        resolved_tts_provider = tts_provider or config.tts_provider
        resolved_tts_model = (
            tts_model
            or config.tts_model
            or get_default_tts_model(resolved_tts_provider)
        )
        resolved_image_provider = image_provider or config.image_provider
        resolved_image_model = (
            image_model
            or config.image_model
            or get_default_image_model(resolved_image_provider)
        )

        self.tts = TextToSpeechService(
            provider=resolved_tts_provider,
            model=resolved_tts_model,
            language=language,
            speaker=speaker,
        )
        self.enable_images = (
            enable_images if enable_images is not None else config.enable_images
        )
        self.image_service = (
            ImageGenerationService(
                provider=resolved_image_provider, model=resolved_image_model
            )
            if self.enable_images
            else None
        )
        code = (target_language or "ru").lower()
        self.target_language = self._LANGUAGE_NAMES.get(code, code.capitalize())
        self.logger.info(
            "Anki Cards Generator initialized (images=%s, image_provider=%s, tts_provider=%s)",
            self.enable_images,
            resolved_image_provider,
            resolved_tts_provider,
        )

    def get_expression_card_info(
        self, model_name: str, prompt: str, expression: str
    ) -> dict:
        """Generate card information for a given expression.

        Args:
            model_name: Name or path of the model to use
            prompt: The prompt template
            expression: The expression to analyze

        Returns:
            Dictionary containing card information

        Raises:
            ModelError: If model inference fails
        """
        # Check cache first
        cached_result = cache_manager.get(expression, prompt, model_name)
        if cached_result:
            self.logger.debug(f"Using cached result for expression: {expression}")
            return cached_result["data"]

        # Substitute target language into the prompt template
        resolved_prompt = prompt.replace("{target_language}", self.target_language)

        try:
            self.logger.info(f"Generating card info for expression: {expression}")
            card_info = model_manager.generate_card_info(
                model_name, resolved_prompt, expression
            )

            # Cache the result
            cache_manager.set(expression, prompt, model_name, card_info)

            return card_info

        except Exception as e:
            self.logger.error(f"Failed to generate card info for '{expression}': {e}")
            raise ModelError(f"Failed to generate card info: {e}") from e

    def _generate_audio_files(
        self, card_data: dict, word: str, audio_format: str = "mp3"
    ) -> dict:
        """Generate audio files for card data fields in parallel.

        Args:
            card_data: Dictionary containing card information
            word: The word being processed
            audio_format: Audio file format

        Returns:
            Updated card data with audio references
        """
        clean_word = word.lower().replace(" ", "_")

        audio_fields = {
            "expression": "audio_expression",
            "definition": "audio_definition",
            "examples": "audio_examples",
            "collocations": "audio_collocations",
            "synonyms": "audio_synonyms",
        }

        def _generate_one(field: str, audio_key: str) -> tuple[str, str]:
            """Return (audio_key, anki_sound_tag_or_empty)."""
            if not card_data.get(field):
                return audio_key, ""
            try:
                filename = f"{clean_word}_{field}.{audio_format}"
                filepath = config.audio_dir / filename
                result = self.tts.generate_audio(card_data[field], str(filepath))
                if result:
                    # Use the actual filename returned by TTS (Qwen3 may change
                    # the extension to .wav regardless of audio_format).
                    actual_filename = Path(result).name
                    self.logger.debug(f"Generated audio for {field}: {actual_filename}")
                    return audio_key, f"[sound:{actual_filename}]"
                self.logger.warning(f"Failed to generate audio for {field}")
                return audio_key, ""
            except Exception as e:
                self.logger.error(f"Error generating audio for {field}: {e}")
                return audio_key, ""

        with ThreadPoolExecutor(max_workers=len(audio_fields)) as executor:
            futures = {
                executor.submit(_generate_one, field, audio_key): audio_key
                for field, audio_key in audio_fields.items()
            }
            for future in futures:
                audio_key, value = future.result()
                card_data[audio_key] = value

        return card_data

    def _generate_image(self, card_data: dict, word: str) -> dict:
        """Generate an illustrative image for the card.

        Stores the Anki ``<img>`` tag in card_data["image"] on success.
        """
        if not self.image_service:
            return card_data

        clean_word = word.lower().replace(" ", "_")
        filename = f"{clean_word}.png"
        filepath = config.images_dir / filename

        try:
            result = self.image_service.generate_image(
                expression=card_data.get("expression", word),
                definition=card_data.get("definition", ""),
                output_path=filepath,
                width=config.sd_image_width,
                height=config.sd_image_height,
            )
            if result:
                actual_filename = Path(result).name
                card_data["image"] = f'<img src="{actual_filename}">'
                self.logger.debug(f"Generated image for '{word}': {actual_filename}")
            else:
                card_data["image"] = ""
        except ImageGenerationError as e:
            self.logger.warning(f"Image generation failed for '{word}': {e}")
            card_data["image"] = ""

        return card_data

    def _save_card_data(self, card_data: dict, word: str) -> None:
        """Save card data to JSON file.

        Args:
            card_data: Dictionary containing card information
            word: The word being processed
        """
        try:
            clean_word = word.lower().replace(" ", "_")
            output_path = config.processed_expressions_dir / f"{clean_word}.json"

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(card_data, f, indent=4, ensure_ascii=False)

            self.logger.debug(f"Saved card data: {output_path}")

        except Exception as e:
            self.logger.error(f"Failed to save card data for '{word}': {e}")
            raise FileProcessingError(f"Failed to save card data: {e}") from e

    def generate_cards_from_words(
        self,
        model_name: str,
        prompt: str,
        words_list: list[str],
        audio_format: str = "mp3",
        progress_callback: Callable[[int, int, str, str], None] | None = None,
    ) -> list[dict]:
        """Generate Anki cards from a list of words.

        Args:
            model_name: Name or path of the model to use
            prompt: The prompt template
            words_list: List of words to process
            audio_format: Audio file format
            progress_callback: Optional callback receiving index, total, word, and state

        Returns:
            List of card data dictionaries

        Raises:
            ModelError: If model processing fails
        """
        cards = []
        failures = []
        total_words = len(words_list)

        self.logger.info(f"Generating cards for {total_words} words")

        for idx, word in enumerate(words_list, 1):
            try:
                self.logger.info(f"Processing word '{word}': {idx}/{total_words}")
                if progress_callback:
                    progress_callback(idx, total_words, word, "start")

                # Generate card data
                card_data = self.get_expression_card_info(model_name, prompt, word)

                # Generate audio files
                card_data = self._generate_audio_files(card_data, word, audio_format)

                # Generate image
                card_data = self._generate_image(card_data, word)

                # Save card data
                self._save_card_data(card_data, word)

                cards.append(card_data)
                if progress_callback:
                    progress_callback(idx, total_words, word, "complete")
                self.logger.info(f"Successfully processed word '{word}'")

            except Exception as e:
                self.logger.error(f"Failed to process word '{word}': {e}")
                failures.append(f"{word}: {e}")
                if progress_callback:
                    progress_callback(idx, total_words, word, "error")
                # Continue with other words instead of failing completely
                continue

        self.logger.info(
            f"Successfully generated {len(cards)} cards out of {total_words} words"
        )
        if not cards and failures:
            raise ModelError(f"No cards were generated. First failure: {failures[0]}")
        return cards

    def create_anki_package(
        self,
        cards_data: list[dict],
        deck_name: str,
        output_path: str,
        card_types: Sequence[str] | None = None,
    ) -> str:
        """Create an Anki package from card data.

        Args:
            cards_data: List of card data dictionaries
            deck_name: Name for the Anki deck
            output_path: Path for the output package
            card_types: Anki card templates to include.

        Returns:
            Path to the created package
        """
        try:
            # Create Anki deck
            deck = create_anki_deck(cards_data, deck_name, card_types=card_types)

            # Create package
            package = genanki.Package(deck)

            # Add only media files referenced by the cards in this package.
            package.media_files = referenced_media_files(
                cards_data,
                audio_dir=config.audio_dir,
                images_dir=config.images_dir,
            )

            # Write package
            package.write_to_file(output_path)

            self.logger.info(f"Created Anki package: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to create Anki package: {e}")
            raise


def main() -> None:
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(description="Generate Anki cards from words.")

    # Input options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--words",
        type=str,
        help="Comma-separated list of words (e.g., 'word1, word2, word3').",
    )
    group.add_argument("--file", type=str, help="Path to a text file containing words.")

    # Configuration options
    parser.add_argument(
        "--audio_format",
        type=str,
        default=config.audio_format,
        help=f"Audio file format (default: {config.audio_format}).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(config.anki_decks_dir / "cards.apkg"),
        help="Output file path for Anki package.",
    )
    parser.add_argument(
        "--deck_name",
        type=str,
        default="Vocabulary Deck",
        help="Name of the Anki deck.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=config.model_path,
        help="Path to a local .gguf file or a liteLLM model identifier like 'openai/gpt-5.4-nano'.",
    )
    parser.add_argument(
        "--tts_provider",
        type=str,
        default=config.tts_provider,
        choices=[TTS_PROVIDER_QWEN3, TTS_PROVIDER_OPENAI, TTS_PROVIDER_GOOGLE],
        help="TTS backend to use.",
    )
    parser.add_argument(
        "--tts_model",
        type=str,
        default=config.tts_model or config.default_tts_model,
        help="Provider-specific TTS model identifier.",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=config.audio_language,
        choices=[
            "en",
            "ru",
            "de",
            "fr",
            "es",
            "it",
            "ja",
            "zh",
            "ko",
            "pt",
            "ar",
            "nl",
            "pl",
            "tr",
        ],
        help=f"Language code of the input words for audio generation (default: {config.audio_language}).",
    )
    parser.add_argument(
        "--target_language",
        type=str,
        default="ru",
        choices=[
            "en",
            "ru",
            "de",
            "fr",
            "es",
            "it",
            "ja",
            "zh",
            "ko",
            "pt",
            "ar",
            "nl",
            "pl",
            "tr",
        ],
        help="Language code for translations in the flashcards (default: ru).",
    )
    parser.add_argument(
        "--learner_level",
        type=str,
        default="auto",
        choices=["auto", "A1", "A2", "B1", "B2", "C1", "C2"],
        help="Target learner level for definitions and example sentences.",
    )
    parser.add_argument(
        "--speaker",
        type=str,
        default=config.qwen3_tts_speaker,
        help="Provider-specific TTS voice / speaker value.",
    )
    parser.add_argument(
        "--image_provider",
        type=str,
        default=config.image_provider,
        choices=[IMAGE_PROVIDER_LOCAL, IMAGE_PROVIDER_OPENAI, IMAGE_PROVIDER_GOOGLE],
        help="Image backend to use.",
    )
    parser.add_argument(
        "--image_model",
        type=str,
        default=config.image_model or config.default_image_model,
        help="Provider-specific image model identifier.",
    )
    parser.add_argument(
        "--log_level",
        type=str,
        default=config.log_level,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level.",
    )
    parser.add_argument(
        "--enable_images",
        action="store_true",
        default=config.enable_images,
        help="Generate illustrative images for each card using Stable Diffusion.",
    )
    parser.add_argument(
        "--clear_cache",
        action="store_true",
        help="Clear cache before processing.",
    )

    args = parser.parse_args()

    # Set up logging
    from .logger import setup_logging

    setup_logging(log_level=args.log_level)
    logger = get_logger(__name__)

    try:
        config.model_path = args.model
        config.audio_format = args.audio_format
        config.tts_provider = args.tts_provider
        config.tts_model = args.tts_model
        config.image_provider = args.image_provider
        config.image_model = args.image_model

        # Validate configuration
        config.validate()

        # Clear cache if requested
        if args.clear_cache:
            cache_manager.clear()
            logger.info("Cache cleared")

        # Parse input words
        words = parse_words(args)
        logger.info(f"Words to process: {words}")

        # Load prompt
        prompt = prompt_with_learner_level(load_prompt(), args.learner_level)

        # Initialize generator
        generator = AnkiCardsGenerator(
            tts_provider=args.tts_provider,
            tts_model=args.tts_model,
            language=args.language,
            speaker=args.speaker,
            target_language=args.target_language,
            enable_images=args.enable_images,
            image_provider=args.image_provider,
            image_model=args.image_model,
        )

        # Generate cards
        cards_data = generator.generate_cards_from_words(
            args.model, prompt, words, audio_format=args.audio_format
        )

        if not cards_data:
            logger.error("No cards were generated successfully")
            return

        # Save cards data
        cards_file = config.json_dir / "cards_data.json"
        with open(cards_file, "w", encoding="utf-8") as f:
            json.dump(cards_data, f, indent=4, ensure_ascii=False)
        logger.info(f"Cards data saved to: {cards_file}")

        # Create Anki package
        package_path = generator.create_anki_package(
            cards_data, args.deck_name, args.output
        )

        logger.info(f"Successfully created Anki deck with {len(cards_data)} cards")
        logger.info(f"Package saved to: {package_path}")

        # Cache statistics
        cache_stats = cache_manager.get_cache_stats()
        logger.info(f"Cache stats: {cache_stats}")

    except Exception as e:
        logger.error(f"Application failed: {e}")
        raise


if __name__ == "__main__":
    main()
