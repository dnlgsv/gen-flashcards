"""Tests for Anki deck creation utilities."""

import pytest

from src.anki_utils import (
    CARD_TYPE_CLOZE,
    CARD_TYPE_PRODUCTION,
    CARD_TYPE_REVERSE,
    _deck_id_from_name,
    create_anki_deck,
)
from src.exceptions import AnkiDeckError


def test_create_anki_deck_success(sample_card_data):
    """Test successful Anki deck creation."""
    cards_data = [sample_card_data]

    deck = create_anki_deck(cards_data, deck_name="Test Deck")

    assert deck.name == "Test Deck"
    assert len(deck.notes) == 1


def test_create_anki_deck_empty_data():
    """Test deck creation with empty data."""
    with pytest.raises(AnkiDeckError):
        create_anki_deck([], deck_name="Empty Deck")


def test_create_anki_deck_missing_fields():
    """Test deck creation with missing fields."""
    incomplete_card = {
        "expression": "test",
        # Missing other required fields
    }

    # Should handle missing fields gracefully
    deck = create_anki_deck([incomplete_card], deck_name="Incomplete Deck")
    assert len(deck.notes) == 1


def test_create_anki_deck_list_fields(sample_card_data):
    """Test handling of list fields in card data."""
    sample_card_data["examples"] = ["Example 1", "Example 2"]
    sample_card_data["synonyms"] = ["synonym1", "synonym2"]

    deck = create_anki_deck([sample_card_data], deck_name="List Test Deck")

    # Check that lists are converted to strings
    note = deck.notes[0]
    examples_field = note.fields[3]  # Examples field
    assert "Example 1<br>Example 2" in examples_field or "Example 1" in examples_field


def test_deck_id_from_name_is_deterministic():
    """Same deck name should always map to the same Anki deck ID."""
    assert _deck_id_from_name("English B2") == _deck_id_from_name("English B2")
    assert _deck_id_from_name("English B2") != _deck_id_from_name("Spanish B2")


def test_create_anki_deck_card_type_options(sample_card_data):
    """Selected non-cloze card types should create matching templates."""
    deck = create_anki_deck(
        [sample_card_data],
        deck_name="Card Types",
        card_types=[CARD_TYPE_REVERSE, CARD_TYPE_PRODUCTION],
    )

    assert len(deck.notes) == 1
    assert [template["name"] for template in deck.notes[0].model.templates] == [
        "Reverse",
        "Production",
    ]


def test_create_anki_deck_cloze_card_type(sample_card_data):
    """Cloze card type should create a cloze note from the first example."""
    sample_card_data["examples"] = ["This is an example sentence."]

    deck = create_anki_deck(
        [sample_card_data],
        deck_name="Cloze Types",
        card_types=[CARD_TYPE_CLOZE],
    )

    assert len(deck.notes) == 1
    assert deck.notes[0].model.model_type == deck.notes[0].model.CLOZE
    assert "{{c1::example}}" in deck.notes[0].fields[0]
