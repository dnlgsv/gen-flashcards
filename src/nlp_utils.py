"""NLP utilities for the Anki Card Generator."""

import argparse
import math
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from typing import BinaryIO, TextIO

import nltk
from nltk.stem import PorterStemmer

try:
    from .exceptions import FileProcessingError
    from .logger import get_logger
except ImportError:
    # Fallback for script execution
    from src.exceptions import FileProcessingError
    from src.logger import get_logger

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*|\d+", re.UNICODE)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_URL_RE = re.compile(r"https?://\S+|www\.\S+|\S+@\S+")
_STEMMER = PorterStemmer()

_STOPWORD_LANGUAGES = {
    "en": "english",
    "de": "german",
    "fr": "french",
    "es": "spanish",
    "it": "italian",
    "pt": "portuguese",
    "ru": "russian",
    "nl": "dutch",
    "tr": "turkish",
}

_BASIC_ENGLISH_WORDS = {
    "also",
    "another",
    "back",
    "because",
    "become",
    "best",
    "better",
    "big",
    "come",
    "day",
    "different",
    "each",
    "even",
    "every",
    "first",
    "give",
    "good",
    "great",
    "high",
    "important",
    "know",
    "large",
    "last",
    "little",
    "long",
    "look",
    "make",
    "many",
    "much",
    "need",
    "new",
    "next",
    "old",
    "only",
    "other",
    "people",
    "place",
    "point",
    "right",
    "same",
    "small",
    "take",
    "thing",
    "think",
    "time",
    "use",
    "want",
    "way",
    "well",
    "work",
    "world",
    "year",
}

_PHRASAL_VERB_PARTICLES = {
    "about",
    "across",
    "after",
    "along",
    "around",
    "away",
    "back",
    "down",
    "for",
    "forward",
    "in",
    "into",
    "off",
    "on",
    "out",
    "over",
    "through",
    "to",
    "together",
    "up",
    "with",
}

_COMMON_VERB_HINTS = {
    "bring",
    "call",
    "carry",
    "come",
    "cut",
    "find",
    "get",
    "give",
    "go",
    "hold",
    "keep",
    "look",
    "make",
    "pick",
    "put",
    "run",
    "set",
    "take",
    "turn",
    "work",
}


@dataclass(frozen=True)
class FlashcardCandidate:
    """A ranked vocabulary candidate extracted from user-provided text."""

    expression: str
    kind: str
    score: float
    frequency: int
    contexts: list[str]
    reason: str


def parse_words(args: argparse.Namespace) -> list[str]:
    """Parse the words either from a comma-separated string or from a file path.

    Args:
        args: Command line arguments containing words or file path

    Returns:
        List of parsed words

    Raises:
        ValueError: If neither words nor file is provided
        FileProcessingError: If file parsing fails
    """
    try:
        words = []
        if args.words:
            # Assume comma-separated words.
            words = [word.strip() for word in args.words.split(",") if word.strip()]
        elif args.file:
            words = parse_file(args.file)
        else:
            raise ValueError("Either --words or --file must be provided.")

        logger.info(f"Successfully parsed {len(words)} words")
        return words

    except Exception as e:
        logger.error(f"Failed to parse words: {e}")
        if isinstance(e, ValueError):
            raise
        raise FileProcessingError(f"Failed to parse words: {e}") from e


def parse_file(file_input: str | TextIO | BinaryIO) -> list[str]:
    """Parse words from a file path or a file-like uploaded object.

    Args:
        file_input: File path string or file-like object

    Returns:
        List of parsed words

    Raises:
        FileProcessingError: If file processing fails
    """
    try:
        if isinstance(file_input, str):
            with open(file_input, encoding="utf-8") as f:
                content = f.read()
        else:
            content = file_input.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8")

        words = []
        # Split content into lines, then by commas, stripping whitespace.
        for line in content.splitlines():
            for word in line.split():
                clean_word = word.strip().rstrip(",.")
                if clean_word:
                    words.append(clean_word)

        logger.debug(f"Parsed {len(words)} words from file")
        return words

    except Exception as e:
        logger.error(f"Failed to parse file: {e}")
        raise FileProcessingError(f"Failed to parse file: {e}") from e


def clean_text(text: str) -> str:
    """Clean and preprocess text data."""
    # Normalize unicode characters
    text = unicodedata.normalize("NFKD", text)
    # Convert to lowercase
    text = text.lower()
    # Remove punctuation (you can adjust the regex to keep certain characters)
    text = re.sub(r"[^\w\s']", "", text)
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def filter_tokens(
    tokens: list[str], stopwords: set[str] | None = None, min_length: int = 2
) -> list[str]:
    """Filter tokens based on stopwords and minimum length."""
    if stopwords is None:
        stopwords = _nltk_stopwords("english")

    filtered = []
    for token in tokens:
        # Filter out numbers or tokens that are too short
        if token.isdigit() or len(token) < min_length:
            continue
        # Optionally filter stopwords
        if token in stopwords:
            continue
        filtered.append(token)
    return filtered


def extract_ngrams(tokens: list[str], n: int = 2, min_freq: int = 2) -> list[str]:
    """Extract n-grams from a list of tokens."""
    ngrams = zip(*[tokens[i:] for i in range(n)], strict=False)
    ngrams = [" ".join(gram) for gram in ngrams]
    freq = Counter(ngrams)
    # Return n-grams that occur at least min_freq times
    return [ng for ng, count in freq.items() if count >= min_freq]


def _language_stopwords(
    language: str, custom_stopwords: set[str] | None = None
) -> set[str]:
    if custom_stopwords is not None:
        return {w.casefold() for w in custom_stopwords}
    stopword_language = _STOPWORD_LANGUAGES.get(language.casefold(), "english")
    try:
        return _nltk_stopwords(stopword_language)
    except Exception:
        return _nltk_stopwords("english")


def _nltk_stopwords(language: str) -> set[str]:
    """Load stopwords on demand and download the corpus only when missing."""
    try:
        return set(nltk.corpus.stopwords.words(language))
    except LookupError:
        nltk.download("stopwords", quiet=True)
        return set(nltk.corpus.stopwords.words(language))


def _split_sentences(text: str) -> list[str]:
    cleaned = _URL_RE.sub(" ", text)
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(cleaned) if s.strip()]


def _tokenize(text: str) -> list[str]:
    return [match.group(0) for match in _TOKEN_RE.finditer(text)]


def _clean_token(token: str) -> str:
    normalized = unicodedata.normalize("NFKC", token).casefold()
    return normalized.strip("'’-.")


def _is_noise_token(token: str, stopwords: set[str], min_length: int = 3) -> bool:
    if not token or token.isdigit() or len(token) < min_length:
        return True
    if token in stopwords:
        return True
    if "." in token or "/" in token or "\\" in token:
        return True
    return bool(re.search(r"(.)\1{3,}", token))


def _normalise_term(term: str, language: str) -> str:
    tokens = [_clean_token(token) for token in _tokenize(term)]
    tokens = [token for token in tokens if token]
    if language.casefold() == "en":
        tokens = [_STEMMER.stem(token) for token in tokens]
    return " ".join(tokens)


def _display_expression(tokens: list[str]) -> str:
    return " ".join(_clean_token(token) for token in tokens if _clean_token(token))


def _context_for_sentence(sentence: str, expression: str, max_length: int = 180) -> str:
    compact = re.sub(r"\s+", " ", sentence).strip()
    if len(compact) <= max_length:
        return compact
    index = compact.casefold().find(expression.casefold())
    if index == -1:
        return compact[: max_length - 3].rstrip() + "..."
    start = max(0, index - 70)
    end = min(len(compact), index + len(expression) + 70)
    snippet = compact[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(compact):
        snippet += "..."
    return snippet


def _candidate_reason(
    kind: str, frequency: int, score: float, contexts: list[str]
) -> str:
    parts = []
    if kind == "phrase":
        parts.append("multi-word expression")
    else:
        parts.append("content word")
    if frequency > 1:
        parts.append(f"appears {frequency} times")
    if contexts:
        parts.append("has clear source context")
    if score >= 25:
        parts.append("high relevance score")
    return "; ".join(parts)


def _level_adjustment(
    expression: str, kind: str, learner_level: str, frequency: int
) -> float:
    level = learner_level.upper()
    if level not in {"A1", "A2", "B1", "B2", "C1", "C2"}:
        return 0.0

    tokens = expression.split()
    longest = max((len(token) for token in tokens), default=0)
    phrase_len = len(tokens)

    if level in {"A1", "A2", "B1"}:
        penalty = 0.0
        if longest > 11:
            penalty += 3.0
        if kind == "phrase" and phrase_len > 3:
            penalty += 2.0
        if frequency >= 3:
            penalty *= 0.35
        return -penalty

    bonus = 0.0
    if longest > 8:
        bonus += 2.0
    if kind == "phrase":
        bonus += min(4.0, phrase_len * 1.2)
    return bonus


def extract_flashcard_candidates(
    text: str,
    *,
    language: str = "en",
    learner_level: str = "auto",
    target_count: int = 30,
    include_phrases: bool = True,
    stopwords: set[str] | None = None,
) -> list[dict[str, object]]:
    """Extract and rank words/phrases that are useful for flashcards.

    The extractor is deterministic and intentionally local: it combines
    frequency, phrase length, stopword filtering, light stemming and source
    context rather than requiring an LLM call.
    """
    cleaned_text = _URL_RE.sub(" ", text or "")
    if not cleaned_text.strip():
        return []

    limit = max(1, min(target_count, 100))
    stopword_set = _language_stopwords(language, stopwords)
    sentences = _split_sentences(cleaned_text)

    counts: Counter[str] = Counter()
    displays: dict[str, str] = {}
    kinds: dict[str, str] = {}
    contexts: dict[str, list[str]] = {}
    first_seen: dict[str, int] = {}
    index_counter = 0

    def add_candidate(expression: str, kind: str, sentence: str) -> None:
        nonlocal index_counter
        expression = re.sub(r"\s+", " ", expression).strip(" -")
        if not expression:
            return
        norm = _normalise_term(expression, language)
        if not norm:
            return
        if norm not in first_seen:
            first_seen[norm] = index_counter
            index_counter += 1
            displays[norm] = expression
            kinds[norm] = kind
            contexts[norm] = []
        counts[norm] += 1
        if len(contexts[norm]) < 2:
            snippet = _context_for_sentence(sentence, expression)
            if snippet and snippet not in contexts[norm]:
                contexts[norm].append(snippet)

    for sentence in sentences:
        raw_tokens = _tokenize(sentence)
        cleaned_tokens = [_clean_token(token) for token in raw_tokens]

        for token in cleaned_tokens:
            if not _is_noise_token(token, stopword_set):
                add_candidate(token, "word", sentence)

        if not include_phrases:
            continue

        for start in range(len(cleaned_tokens)):
            for size in range(2, 5):
                window = cleaned_tokens[start : start + size]
                if len(window) < size:
                    continue
                content = [
                    token
                    for token in window
                    if not _is_noise_token(token, stopword_set, min_length=2)
                ]
                is_phrasal_verb = (
                    size == 2
                    and window[0] in _COMMON_VERB_HINTS
                    and window[1] in _PHRASAL_VERB_PARTICLES
                )
                if len(content) < 2 and not is_phrasal_verb:
                    continue
                if window[0] in stopword_set and not is_phrasal_verb:
                    continue
                if (
                    window[-1] in stopword_set
                    and window[-1] not in _PHRASAL_VERB_PARTICLES
                ):
                    continue
                if any(token.isdigit() for token in window):
                    continue
                add_candidate(_display_expression(window), "phrase", sentence)

    scored: list[FlashcardCandidate] = []
    for norm, frequency in counts.items():
        expression = displays[norm]
        kind = kinds[norm]
        tokens = expression.split()
        token_lengths = [len(token) for token in tokens]
        specificity = sum(min(length, 12) for length in token_lengths) / max(
            len(tokens), 1
        )
        score = math.log1p(frequency) * 8.0 + specificity
        if kind == "phrase":
            score += 9.0 + min(6.0, len(tokens) * 1.5)
            if frequency > 1:
                score += 5.0
        if expression in _BASIC_ENGLISH_WORDS:
            score -= 7.0
        if frequency == 1 and kind == "phrase":
            score -= 2.0
        score += _level_adjustment(expression, kind, learner_level, frequency)

        if score <= 0:
            continue
        scored.append(
            FlashcardCandidate(
                expression=expression,
                kind=kind,
                score=round(score, 2),
                frequency=frequency,
                contexts=contexts.get(norm, []),
                reason=_candidate_reason(
                    kind, frequency, score, contexts.get(norm, [])
                ),
            )
        )

    scored.sort(
        key=lambda item: (
            -item.score,
            first_seen[_normalise_term(item.expression, language)],
        )
    )
    return [asdict(candidate) for candidate in scored[:limit]]


def prepare_flashcard_candidates(
    file_input: str | TextIO | BinaryIO,
    stopwords: set[str] | None = None,
) -> list[dict[str, object]]:
    """Prepare flashcard candidates from a file input.

    Args:
        file_input: File path or file-like uploaded object.
        stopwords: Optional set of stopwords to filter out.

    Returns:
        Ranked structured candidate words and phrases.
    """
    raw_content = parse_file(file_input)
    text = " ".join(raw_content)
    flashcard_candidates = extract_flashcard_candidates(text, stopwords=stopwords)
    logger.debug(
        f"Prepared {len(flashcard_candidates)} candidates from {len(raw_content)} words"
    )
    return flashcard_candidates
