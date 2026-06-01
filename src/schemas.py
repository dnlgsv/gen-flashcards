"""Pydantic schemas for validating LLM output in the LM Anki Cards Creator application."""

from collections.abc import Iterable

from pydantic import BaseModel, field_validator


class CardInfo(BaseModel):
    """Schema for the card information returned by the language model."""

    original_form: str = ""
    part_of_speech: str = ""
    definition: str = ""
    examples: list[str] = []
    synonyms: list[str] = []
    antonyms: list[str] = []
    collocations: list[str] = []
    translations: list[str] = []
    cefr_level: str = "?"
    topics: list[str] = []
    expression: str = ""

    @field_validator(
        "examples",
        "synonyms",
        "antonyms",
        "collocations",
        "translations",
        "topics",
        mode="before",
    )
    @classmethod
    def coerce_to_list(cls, v: object) -> list[str]:
        """Accept None or a bare string instead of a list."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v else []
        if isinstance(v, Iterable):
            return [str(item) for item in v]
        return [str(v)]

    @field_validator("cefr_level", mode="before")
    @classmethod
    def normalise_cefr(cls, v: object) -> str:
        """Accept None or unknown values gracefully."""
        if not v:
            return "?"
        return str(v).strip()
