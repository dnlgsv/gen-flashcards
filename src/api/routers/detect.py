"""POST /api/detect-language endpoint — auto-detect input text language."""

from __future__ import annotations

from fastapi import APIRouter

from ..schemas import DetectLanguageRequest, DetectLanguageResponse

router = APIRouter(tags=["Language Detection"])

# ---------------------------------------------------------------------------
# Lingua detector — built once at module load time.
# Only the 14 languages supported by Qwen3 TTS are included so the detector
# focuses on the relevant language space and avoids spurious detections.
# ---------------------------------------------------------------------------

_detector = None
_LINGUA_AVAILABLE = False

try:
    from lingua import Language, LanguageDetectorBuilder

    _SUPPORTED_LANGUAGES = [
        Language.ARABIC,
        Language.CHINESE,
        Language.DUTCH,
        Language.ENGLISH,
        Language.FRENCH,
        Language.GERMAN,
        Language.ITALIAN,
        Language.JAPANESE,
        Language.KOREAN,
        Language.POLISH,
        Language.PORTUGUESE,
        Language.RUSSIAN,
        Language.SPANISH,
        Language.TURKISH,
    ]

    _detector = LanguageDetectorBuilder.from_languages(*_SUPPORTED_LANGUAGES).build()
    _LINGUA_AVAILABLE = True
except Exception:
    # ImportError or any initialization error — detection will return null
    pass


@router.post("/detect-language", response_model=DetectLanguageResponse)
async def detect_language(body: DetectLanguageRequest) -> DetectLanguageResponse:
    """Detect the language of the provided text.

    Returns the ISO-639-1 code and human-readable name of the detected language,
    or null values when detection fails or the library is unavailable.
    """
    if not _LINGUA_AVAILABLE or _detector is None or not body.text.strip():
        return DetectLanguageResponse(language=None, language_name=None)

    try:
        lang = _detector.detect_language_of(body.text)
    except Exception:
        return DetectLanguageResponse(language=None, language_name=None)

    if lang is None:
        return DetectLanguageResponse(language=None, language_name=None)

    code = lang.iso_code_639_1.name.lower()
    name = lang.name.capitalize()
    return DetectLanguageResponse(language=code, language_name=name)
