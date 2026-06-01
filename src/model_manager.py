"""Model management for the LM Anki Cards Creator application."""

import json
import os
import re
import threading
from typing import Any

from .config import config
from .exceptions import ModelError, ModelInferenceError, ModelLoadError
from .llm_catalog import (
    LOCAL_GGUF_PROVIDER,
    extract_local_model_path,
    is_api_model_identifier,
    is_openai_alias,
    normalize_model_name,
)
from .logger import LoggerMixin
from .schemas import CardInfo


def _is_openai_model(model_name: str) -> bool:
    """Return True if *model_name* refers to an OpenAI hosted model."""
    normalized = normalize_model_name(model_name)
    return is_openai_alias(model_name) or normalized.startswith("openai/")


def _extract_json(text: str) -> str:
    """Extract a JSON object from an LLM response that may contain markdown fences."""
    # Try to find a fenced JSON block first: ```json ... ```
    fenced = re.search(r"```json\s*(.*?)```", text, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    # Fallback: find the outermost { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text.strip()


class ModelManager(LoggerMixin):
    """Manages language model instances with singleton pattern for local models."""

    _instances: dict[str, Any] = {}
    _provider_lock = threading.Lock()
    _provider_registered = False

    def __init__(self) -> None:
        """Initialize model manager."""
        self.logger.info("Model manager initialized")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_card_info(
        self,
        model_name: str,
        prompt: str,
        expression: str,
    ) -> dict[str, Any]:
        """Generate card information using the specified model.

        Args:
            model_name: Name or path of the model to use.
            prompt: The prompt template (system instructions).
            expression: The expression to analyse.

        Returns:
            Validated dictionary containing card information.

        Raises:
            ModelInferenceError: If model inference or output validation fails.
        """
        try:
            normalized_model = normalize_model_name(model_name)
            return self._generate_with_litellm(normalized_model, prompt, expression)
        except ModelError:
            raise
        except Exception as e:
            self.logger.error(f"Model inference failed for '{expression}': {e}")
            raise ModelInferenceError(f"Model inference failed: {e}") from e

    def get_model(self, model_name: str) -> Any:
        """Get or load a local Llama model instance.

        Args:
            model_name: Path to the GGUF model file.

        Returns:
            Loaded Llama instance.

        Raises:
            ModelLoadError: If the model fails to load.
        """
        if model_name in self._instances:
            self.logger.debug(f"Returning cached model: {model_name}")
            return self._instances[model_name]

        try:
            self.logger.info(f"Loading model: {model_name}")
            model = self._load_local_model(model_name)
            self._instances[model_name] = model
            self.logger.info(f"Model loaded successfully: {model_name}")
            return model
        except Exception as e:
            self.logger.error(f"Failed to load model '{model_name}': {e}")
            raise ModelLoadError(f"Failed to load model '{model_name}': {e}") from e

    def reset_model(self, model_name: str) -> None:
        """Unload a specific local model instance."""
        if model_name in self._instances:
            model = self._instances[model_name]
            try:
                from llama_cpp import Llama

                if isinstance(model, Llama):
                    model.reset()
            except Exception as e:
                self.logger.warning(f"Failed to reset model {model_name}: {e}")
            del self._instances[model_name]
            self.logger.info(f"Model instance removed: {model_name}")

    def clear_all_models(self) -> None:
        """Unload all local model instances."""
        for model_name in list(self._instances.keys()):
            self.reset_model(model_name)
        self.logger.info("All model instances cleared")

    def get_loaded_models(self) -> list[str]:
        """Return names of currently loaded local models."""
        return list(self._instances.keys())

    @classmethod
    def _ensure_local_provider_registered(cls, manager: "ModelManager") -> None:
        """Register the local GGUF provider with liteLLM once per process."""
        if cls._provider_registered:
            return

        with cls._provider_lock:
            if cls._provider_registered:
                return

            try:
                import litellm
                from litellm.llms.custom_llm import CustomLLM
            except Exception as e:
                raise ModelInferenceError(
                    "liteLLM is not installed. Install project dependencies again."
                ) from e

            class LocalGGUFProvider(CustomLLM):
                """liteLLM custom provider that preserves in-process GGUF inference."""

                def completion(self, *args: Any, **kwargs: Any) -> Any:
                    model_identifier = kwargs["model"]
                    messages = kwargs.get("messages") or []
                    optional_params = kwargs.get("optional_params") or {}
                    model_response = kwargs["model_response"]

                    model_path = extract_local_model_path(model_identifier)
                    model = manager.get_model(model_path)
                    response = model.create_chat_completion(
                        messages=messages,
                        temperature=optional_params.get(
                            "temperature", config.temperature
                        ),
                        max_tokens=optional_params.get("max_tokens", config.max_tokens),
                    )

                    answer = response["choices"][0]["message"]["content"].strip()
                    model_response.model = model_identifier
                    model_response.choices[0].message.content = answer
                    finish_reason = response["choices"][0].get("finish_reason")
                    if finish_reason:
                        model_response.choices[0].finish_reason = finish_reason

                    usage = response.get("usage") or {}
                    if getattr(model_response, "usage", None) is not None:
                        model_response.usage.prompt_tokens = usage.get(
                            "prompt_tokens", 0
                        )
                        model_response.usage.completion_tokens = usage.get(
                            "completion_tokens", 0
                        )
                        model_response.usage.total_tokens = usage.get("total_tokens", 0)

                    return model_response

            existing = list(getattr(litellm, "custom_provider_map", []) or [])
            if not any(
                item.get("provider") == LOCAL_GGUF_PROVIDER for item in existing
            ):
                existing.append(
                    {
                        "provider": LOCAL_GGUF_PROVIDER,
                        "custom_handler": LocalGGUFProvider(),
                    }
                )
                litellm.custom_provider_map = existing

            cls._provider_registered = True

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_local_model(self, model_path: str) -> Any:
        """Load a local GGUF model via llama-cpp-python."""
        try:
            from llama_cpp import Llama

            return Llama(
                model_path=model_path,
                n_ctx=config.n_ctx,
                n_gpu_layers=config.n_gpu_layers,
                verbose=False,
            )
        except Exception as e:
            raise ModelLoadError(f"Failed to load local model: {e}") from e

    @staticmethod
    def _user_message(expression: str, model_path: str) -> str:
        base = f"The expression to analyze is: ```{expression}```"
        if "qwen3" in model_path.lower():
            base += " /no_think"
        return base

    @staticmethod
    def _validate_provider_credentials(model_name: str) -> None:
        provider = model_name.split("/", 1)[0]
        required_env = {
            "openai": ["OPENAI_API_KEY"],
            "anthropic": ["ANTHROPIC_API_KEY"],
            "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
            "xai": ["XAI_API_KEY"],
            "deepseek": ["DEEPSEEK_API_KEY"],
            "groq": ["GROQ_API_KEY"],
            "openrouter": ["OPENROUTER_API_KEY"],
        }
        env_names = required_env.get(provider)
        if env_names and not any(os.getenv(name) for name in env_names):
            joined = " or ".join(env_names)
            raise ModelInferenceError(f"{joined} is not set. Add it to your .env file.")

    def _generate_with_litellm(
        self,
        model_name: str,
        prompt: str,
        expression: str,
    ) -> dict[str, Any]:
        """Run inference through liteLLM for both local and remote models."""
        try:
            self._ensure_local_provider_registered(self)
            self._validate_provider_credentials(model_name)

            from litellm import completion

            user_message = self._user_message(
                expression,
                extract_local_model_path(model_name),
            )
            response = completion(
                model=model_name,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
            answer = response.choices[0].message.content or ""
            return self._parse_and_validate(answer, expression)
        except ModelInferenceError:
            raise
        except Exception as e:
            route = "API" if is_api_model_identifier(model_name) else "local"
            raise ModelInferenceError(f"liteLLM {route} inference failed: {e}") from e

    def _parse_and_validate(self, answer: str, expression: str) -> dict[str, Any]:
        """Extract JSON from *answer*, validate it with Pydantic, and return a dict.

        Raises:
            ModelInferenceError: If JSON cannot be parsed or schema validation fails.
        """
        try:
            json_text = _extract_json(answer)
            raw = json.loads(json_text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response for '{expression}': {e}")
            self.logger.debug(f"Raw response: {answer[:500]}")
            raise ModelInferenceError(
                f"Failed to parse model response as JSON: {e}"
            ) from e

        try:
            raw["expression"] = expression
            if not raw.get("original_form"):
                raw["original_form"] = expression
            # Filter out generic topic noise
            if "topics" in raw and isinstance(raw["topics"], list):
                raw["topics"] = [
                    t for t in raw["topics"] if t.lower() != "language learning"
                ]
            card = CardInfo.model_validate(raw)
            return card.model_dump()
        except Exception as e:
            self.logger.error(f"Schema validation failed for '{expression}': {e}")
            raise ModelInferenceError(
                f"Model output failed schema validation: {e}"
            ) from e


# Global model manager instance
model_manager = ModelManager()
