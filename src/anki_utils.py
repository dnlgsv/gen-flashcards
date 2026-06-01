"""Anki deck creation utilities for the LM Anki Cards Creator application."""

import hashlib
import html
import json
import re
import sqlite3
import tempfile
import zipfile
from collections.abc import Sequence
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import genanki

from .exceptions import AnkiDeckError


def _normalize_field(value: str | list[str] | None) -> str:
    """Convert list fields to HTML-friendly strings and ensure a string output.

    Args:
        value: The raw value from the card dictionary (string or list of strings).

    Returns:
        A string suitable for an Anki field (lists joined with ``<br>``).
    """
    if value is None:
        return ""

    if isinstance(value, list):
        # Join list elements with ``<br>`` to preserve newlines inside Anki cards.
        return "<br>".join(str(v) for v in value if v)

    # Fall back to plain string conversion for any other type
    return str(value)


class _ImageSrcParser(HTMLParser):
    """Collect image src attributes from generated Anki HTML snippets."""

    def __init__(self) -> None:
        super().__init__()
        self.srcs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        for name, value in attrs:
            if name.lower() == "src" and value:
                self.srcs.append(value)


def referenced_media_files(
    cards_data: list[dict],
    audio_dir: Path,
    images_dir: Path,
) -> list[str]:
    """Return existing media paths referenced by card sound/image fields."""
    audio_names: set[str] = set()
    image_names: set[str] = set()

    for card in cards_data:
        for value in card.values():
            if not isinstance(value, str):
                continue
            audio_names.update(
                Path(match).name for match in re.findall(r"\[sound:([^\]]+)\]", value)
            )

            parser = _ImageSrcParser()
            parser.feed(value)
            image_names.update(Path(src).name for src in parser.srcs)

    media_files: list[str] = []
    for filename in sorted(audio_names):
        path = audio_dir / filename
        if path.exists():
            media_files.append(str(path))
    for filename in sorted(image_names):
        path = images_dir / filename
        if path.exists():
            media_files.append(str(path))
    return media_files


# Keep the *model ID* and *deck ID* stable across runs to avoid card dupes inside Anki.
# If these constants change, Anki will treat the cards as new (duplicate) cards.
_MODEL_ID: int = 2137741800
_CLOZE_MODEL_ID: int = 2137741801
_DECK_ID_BASE: int = 2059400110
CARD_TYPE_RECOGNITION = "recognition"
CARD_TYPE_REVERSE = "reverse"
CARD_TYPE_PRODUCTION = "production"
CARD_TYPE_CLOZE = "cloze"
SUPPORTED_CARD_TYPES = {
    CARD_TYPE_RECOGNITION,
    CARD_TYPE_REVERSE,
    CARD_TYPE_PRODUCTION,
    CARD_TYPE_CLOZE,
}

_APKG_COLLECTION_NAMES = ("collection.anki2", "collection.anki21")
_LIST_FIELD_KEYS = {
    "examples",
    "synonyms",
    "antonyms",
    "collocations",
    "translations",
    "topics",
}
_FIELD_NAME_TO_CARD_KEY = {
    "expression": "expression",
    "original form": "original_form",
    "original_form": "original_form",
    "definition": "definition",
    "examples": "examples",
    "synonyms": "synonyms",
    "antonyms": "antonyms",
    "collocations": "collocations",
    "part of speech": "part_of_speech",
    "part_of_speech": "part_of_speech",
    "translations": "translations",
    "topics": "topics",
    "audio expression": "audio_expression",
    "audio_expression": "audio_expression",
    "audio definition": "audio_definition",
    "audio_definition": "audio_definition",
    "audio examples": "audio_examples",
    "audio_examples": "audio_examples",
    "audio collocations": "audio_collocations",
    "audio_collocations": "audio_collocations",
    "audio synonyms": "audio_synonyms",
    "audio_synonyms": "audio_synonyms",
    "cefr level": "cefr_level",
    "cefr_level": "cefr_level",
    "image": "image",
}


def _empty_card() -> dict[str, Any]:
    return {
        "expression": "",
        "original_form": "",
        "part_of_speech": "",
        "definition": "",
        "examples": [],
        "synonyms": [],
        "antonyms": [],
        "collocations": [],
        "translations": [],
        "cefr_level": "",
        "topics": [],
        "audio_expression": "",
        "audio_definition": "",
        "audio_examples": "",
        "audio_collocations": "",
        "audio_synonyms": "",
        "image": "",
    }


def _split_anki_list_field(value: str) -> list[str]:
    normalized = re.sub(r"(?i)<br\s*/?>", "\n", value)
    return [
        html.unescape(item.strip()) for item in normalized.splitlines() if item.strip()
    ]


def _normalize_imported_value(key: str, value: str) -> str | list[str]:
    if key in _LIST_FIELD_KEYS:
        return _split_anki_list_field(value)
    return html.unescape(value.strip())


def _deck_id_from_name(deck_name: str) -> int:
    """Return a stable genanki deck ID derived from the deck name."""
    digest = hashlib.sha256(deck_name.encode("utf-8")).hexdigest()
    return _DECK_ID_BASE + int(digest[:8], 16) % 1_000_000


def _card_back_template() -> str:
    return (
        "{{FrontSide}}<hr id='answer'>"
        "{{#Image}}<div style='text-align:center;margin-bottom:10px;'>{{Image}}</div>{{/Image}}"
        "<b>Expression:</b> {{Expression}}<br>"
        "<b>Original Form:</b> {{Original Form}}<br>"
        "<b>Definition:</b> {{Definition}}<br>"
        "<b>Examples:</b><br>{{Examples}}<br>"
        "<b>Synonyms:</b> {{Synonyms}}<br>"
        "<b>Antonyms:</b> {{Antonyms}}<br>"
        "<b>Collocations:</b> {{Collocations}}<br>"
        "<b>Translations:</b> {{Translations}}<br>"
        "<b>Topics:</b> {{Topics}}<br>"
        "<b>Part of Speech:</b> {{Part of Speech}}<br>"
        "<b>CEFR Level:</b> {{CEFR Level}}<br>"
        "{{Audio Definition}}<br>{{Audio Examples}}<br>"
        "{{Audio Collocations}}<br>{{Audio Synonyms}}"
    )


def _templates_for_card_types(card_types: Sequence[str]) -> list[dict[str, str]]:
    templates: list[dict[str, str]] = []
    answer = _card_back_template()

    if CARD_TYPE_RECOGNITION in card_types:
        templates.append(
            {
                "name": "Recognition",
                "qfmt": "{{Expression}}<br>{{Audio Expression}}",
                "afmt": answer,
            }
        )
    if CARD_TYPE_REVERSE in card_types:
        templates.append(
            {
                "name": "Reverse",
                "qfmt": "{{Definition}}",
                "afmt": answer,
            }
        )
    if CARD_TYPE_PRODUCTION in card_types:
        templates.append(
            {
                "name": "Production",
                "qfmt": "{{Definition}}<br><br>{{type:Expression}}",
                "afmt": answer,
            }
        )

    return templates


def _first_item(value: str | list[str] | None) -> str:
    if isinstance(value, list):
        return next((str(item) for item in value if item), "")
    return str(value or "")


def _cloze_text(card: dict) -> str:
    expression = _normalize_field(card.get("expression"))
    example = _first_item(card.get("examples"))
    if expression and example:
        pattern = re.compile(re.escape(expression), flags=re.IGNORECASE)
        cloze_example, count = pattern.subn(
            f"{{{{c1::{expression}}}}}", example, count=1
        )
        if count:
            return cloze_example
    definition = _normalize_field(card.get("definition"))
    if definition:
        return f"{{{{c1::{expression}}}}} - {definition}"
    return f"{{{{c1::{expression}}}}}"


def create_anki_deck(
    cards_data: list[dict],
    deck_name: str = "Vocabulary Deck",
    card_types: Sequence[str] | None = None,
) -> genanki.Deck:  # noqa: D401
    """Create a ``genanki.Deck`` from card dictionaries.

    Missing keys are filled with empty strings so that the function degrades
    gracefully for incomplete card data.

    Args:
        cards_data: List containing the card information dictionaries.
        deck_name: The name of the resulting Anki deck.
        card_types: Anki card templates to include. Defaults to recognition.

    Returns:
        A ``genanki.Deck`` instance populated with notes derived from
        *cards_data*.

    Raises:
        AnkiDeckError: If *cards_data* is empty or deck creation fails.
    """

    if not cards_data:
        raise AnkiDeckError("No card data supplied for deck creation")

    selected_card_types = card_types or [CARD_TYPE_RECOGNITION]
    invalid_card_types = sorted(set(selected_card_types) - SUPPORTED_CARD_TYPES)
    if invalid_card_types:
        raise AnkiDeckError(
            f"Unsupported card type(s): {', '.join(invalid_card_types)}"
        )

    # Define the model only once. All notes will share it.
    field_names = [
        "Expression",
        "Original Form",
        "Definition",
        "Examples",
        "Synonyms",
        "Antonyms",
        "Collocations",
        "Part of Speech",
        "Translations",
        "Topics",
        "Audio Expression",
        "Audio Definition",
        "Audio Examples",
        "Audio Collocations",
        "Audio Synonyms",
        "CEFR Level",
        "Image",
    ]

    templates = _templates_for_card_types(selected_card_types)
    model = (
        genanki.Model(
            _MODEL_ID,
            "Vocabulary Model",
            fields=[{"name": n} for n in field_names],
            templates=templates,
        )
        if templates
        else None
    )
    cloze_model = (
        genanki.Model(
            _CLOZE_MODEL_ID,
            "Vocabulary Cloze Model",
            fields=[{"name": "Text"}, {"name": "Back Extra"}],
            templates=[
                {
                    "name": "Cloze",
                    "qfmt": "{{cloze:Text}}",
                    "afmt": "{{cloze:Text}}<br><hr id='answer'>{{Back Extra}}",
                }
            ],
            model_type=genanki.Model.CLOZE,
        )
        if CARD_TYPE_CLOZE in selected_card_types
        else None
    )

    # Create a unique, stable deck ID per deck name to avoid duplicate imports.
    deck_id = _deck_id_from_name(deck_name)
    deck = genanki.Deck(deck_id, deck_name)

    # Populate notes
    for card in cards_data:
        try:
            fields = [
                _normalize_field(card.get("expression")),
                _normalize_field(card.get("original_form")),
                _normalize_field(card.get("definition")),
                _normalize_field(card.get("examples")),
                _normalize_field(card.get("synonyms")),
                _normalize_field(card.get("antonyms")),
                _normalize_field(card.get("collocations")),
                _normalize_field(card.get("part_of_speech")),
                _normalize_field(card.get("translations")),
                _normalize_field(card.get("topics")),
                _normalize_field(card.get("audio_expression")),
                _normalize_field(card.get("audio_definition")),
                _normalize_field(card.get("audio_examples")),
                _normalize_field(card.get("audio_collocations")),
                _normalize_field(card.get("audio_synonyms")),
                _normalize_field(card.get("cefr_level")),
                _normalize_field(card.get("image")),
            ]

            if model is not None:
                note = genanki.Note(model=model, fields=fields)
                deck.add_note(note)
            if cloze_model is not None:
                deck.add_note(
                    genanki.Note(
                        model=cloze_model,
                        fields=[
                            _cloze_text(card),
                            (
                                f"<b>{_normalize_field(card.get('expression'))}</b><br>"
                                f"{_normalize_field(card.get('definition'))}<br>"
                                f"{_normalize_field(card.get('audio_expression'))}"
                            ),
                        ],
                    )
                )
        except Exception as exc:  # Catch genanki errors and wrap them
            raise AnkiDeckError(
                f"Failed to create note for expression '{card.get('expression')}'. Error: {exc}"
            ) from exc

    return deck


def _load_media_map(archive: zipfile.ZipFile) -> dict[str, str]:
    try:
        with archive.open("media") as media_file:
            raw_media = json.loads(media_file.read().decode("utf-8"))
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return {
        str(member): Path(str(filename)).name
        for member, filename in raw_media.items()
        if str(filename).strip()
    }


def _extract_imported_media(
    archive: zipfile.ZipFile,
    media_map: dict[str, str],
    audio_dir: Path,
    images_dir: Path,
) -> None:
    audio_exts = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac"}
    image_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}

    audio_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    for member, filename in media_map.items():
        suffix = Path(filename).suffix.lower()
        if suffix in audio_exts:
            output_dir = audio_dir
        elif suffix in image_exts:
            output_dir = images_dir
        else:
            continue

        try:
            data = archive.read(member)
        except KeyError:
            continue
        (output_dir / filename).write_bytes(data)


def _model_field_names(models: dict[str, Any], model_id: int) -> list[str]:
    model = models.get(str(model_id), {})
    fields = model.get("flds", [])
    return [str(field.get("name", "")) for field in fields if isinstance(field, dict)]


def _card_from_note(field_names: list[str], field_values: list[str]) -> dict[str, Any]:
    card = _empty_card()
    mapped = False

    for index, value in enumerate(field_values):
        field_name = field_names[index] if index < len(field_names) else ""
        key = _FIELD_NAME_TO_CARD_KEY.get(field_name.strip().lower())
        if not key:
            continue
        card[key] = _normalize_imported_value(key, value)
        mapped = True

    if not mapped:
        card["expression"] = html.unescape(
            (field_values[0] if field_values else "").strip()
        )
        if len(field_values) > 1:
            card["definition"] = html.unescape(field_values[1].strip())

    if not card["original_form"]:
        card["original_form"] = card["expression"]
    return card


def import_anki_package(
    apkg_path: Path,
    audio_dir: Path,
    images_dir: Path,
) -> dict[str, Any]:
    """Read an Anki .apkg file and return editable card dictionaries."""
    try:
        archive = zipfile.ZipFile(apkg_path)
    except zipfile.BadZipFile as exc:
        raise AnkiDeckError("Uploaded file is not a valid .apkg archive") from exc

    with archive:
        collection_name = next(
            (name for name in _APKG_COLLECTION_NAMES if name in archive.namelist()),
            None,
        )
        if collection_name is None:
            raise AnkiDeckError("Uploaded .apkg does not contain an Anki collection")

        media_map = _load_media_map(archive)
        _extract_imported_media(archive, media_map, audio_dir, images_dir)

        with tempfile.TemporaryDirectory() as temp_dir:
            collection_path = Path(temp_dir) / collection_name
            collection_path.write_bytes(archive.read(collection_name))

            conn = sqlite3.connect(collection_path)
            try:
                cursor = conn.execute("select decks, models from col limit 1")
                row = cursor.fetchone()
                cursor.close()
                if row is None:
                    raise AnkiDeckError("Uploaded .apkg collection is empty")

                try:
                    decks = json.loads(row[0])
                    models = json.loads(row[1])
                except json.JSONDecodeError as exc:
                    raise AnkiDeckError("Uploaded .apkg metadata is invalid") from exc

                cursor = conn.execute(
                    """
                    select n.id, n.mid, n.flds, min(c.did) as deck_id
                    from notes n
                    left join cards c on c.nid = n.id
                    group by n.id, n.mid, n.flds
                    order by n.id
                    """
                )
                note_rows = cursor.fetchall()
                cursor.close()
            finally:
                conn.close()

    if not note_rows:
        raise AnkiDeckError("Uploaded .apkg does not contain any notes")

    deck_id = str(note_rows[0][3]) if note_rows[0][3] is not None else ""
    deck_name = decks.get(deck_id, {}).get("name") if deck_id else None
    if not deck_name:
        deck_name = next(
            (
                str(deck.get("name"))
                for deck in decks.values()
                if isinstance(deck, dict) and deck.get("name")
            ),
            apkg_path.stem,
        )

    cards = [
        _card_from_note(_model_field_names(models, int(model_id)), flds.split("\x1f"))
        for _, model_id, flds, _ in note_rows
    ]
    return {
        "deck_name": str(deck_name),
        "cards": cards,
        "card_count": len(cards),
    }
