"""Tests for src/schemas.py — CardInfo Pydantic validation."""

from src.schemas import CardInfo


def _base() -> dict:
    return {
        "original_form": "test",
        "part_of_speech": "noun",
        "definition": "A test word.",
        "examples": ["This is an example.", "Another example."],
        "synonyms": ["word", "term"],
        "antonyms": ["antonym"],
        "collocations": ["test word"],
        "translations": ["слово"],
        "cefr_level": "B2",
        "topics": ["language"],
        "expression": "test",
    }


def test_valid_card_info():
    card = CardInfo.model_validate(_base())
    assert card.expression == "test"
    assert card.original_form == "test"
    assert card.cefr_level == "B2"
    assert card.part_of_speech == "noun"


def test_missing_optional_fields_use_defaults():
    data = {"definition": "minimal", "part_of_speech": "noun"}
    card = CardInfo.model_validate(data)
    assert card.synonyms == []
    assert card.antonyms == []
    assert card.examples == []
    assert card.cefr_level == "?"
    assert card.expression == ""
    assert card.original_form == ""


def test_string_coerced_to_list():
    data = _base()
    data["synonyms"] = "single"
    data["translations"] = "одно слово"
    card = CardInfo.model_validate(data)
    assert card.synonyms == ["single"]
    assert card.translations == ["одно слово"]


def test_none_coerced_to_empty_list():
    data = _base()
    data["synonyms"] = None
    data["collocations"] = None
    card = CardInfo.model_validate(data)
    assert card.synonyms == []
    assert card.collocations == []


def test_empty_string_cefr_becomes_question_mark():
    data = _base()
    data["cefr_level"] = ""
    card = CardInfo.model_validate(data)
    assert card.cefr_level == "?"


def test_none_cefr_becomes_question_mark():
    data = _base()
    data["cefr_level"] = None
    card = CardInfo.model_validate(data)
    assert card.cefr_level == "?"


def test_unknown_extra_fields_ignored():
    """Pydantic defaults: extra fields are ignored."""
    data = _base()
    data["unknown_field"] = "should be ignored"
    card = CardInfo.model_validate(data)
    assert not hasattr(card, "unknown_field")


def test_model_dump_returns_dict():
    card = CardInfo.model_validate(_base())
    result = card.model_dump()
    assert isinstance(result, dict)
    assert result["expression"] == "test"
    assert result["original_form"] == "test"
    assert isinstance(result["examples"], list)
