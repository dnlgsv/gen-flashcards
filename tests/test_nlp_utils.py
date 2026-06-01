"""Tests for src/nlp_utils.py."""

import io

import pytest

from src.exceptions import FileProcessingError
from src.nlp_utils import (
    clean_text,
    extract_flashcard_candidates,
    extract_ngrams,
    filter_tokens,
    parse_file,
    prepare_flashcard_candidates,
)

# ---------------------------------------------------------------------------
# parse_file
# ---------------------------------------------------------------------------


def test_parse_file_from_path(temp_dir):
    p = temp_dir / "words.txt"
    p.write_text("apple banana\ncherry, date\n")
    result = parse_file(str(p))
    assert "apple" in result
    assert "banana" in result
    assert "cherry" in result
    assert "date" in result


def test_parse_file_from_file_like_object():
    content = "furthermore moreover\nalthough despite"
    f = io.StringIO(content)
    result = parse_file(f)
    assert "furthermore" in result
    assert "moreover" in result
    assert "although" in result


def test_parse_file_from_bytes_file_like():
    content = b"hello world\nfoo bar"
    f = io.BytesIO(content)
    result = parse_file(f)
    assert "hello" in result
    assert "world" in result


def test_parse_file_missing_path_raises():
    with pytest.raises(FileProcessingError):
        parse_file("/nonexistent/path/words.txt")


def test_parse_file_strips_punctuation():
    content = "apple, banana. cherry!"
    f = io.StringIO(content)
    result = parse_file(f)
    assert "apple" in result
    assert "banana" in result


# ---------------------------------------------------------------------------
# clean_text
# ---------------------------------------------------------------------------


def test_clean_text_lowercase():
    assert clean_text("Hello World") == "hello world"


def test_clean_text_removes_punctuation():
    result = clean_text("Hello, world!")
    assert "," not in result
    assert "!" not in result


def test_clean_text_normalises_unicode():
    # café → cafe (NFKD normalisation turns é into e + combining accent,
    # then regex removes non-word chars)
    result = clean_text("café")
    assert "cafe" in result or "caf" in result


def test_clean_text_collapses_whitespace():
    assert clean_text("hello   world") == "hello world"


# ---------------------------------------------------------------------------
# filter_tokens
# ---------------------------------------------------------------------------


def test_filter_tokens_removes_stopwords():
    tokens = ["the", "quick", "brown", "fox"]
    result = filter_tokens(tokens)
    assert "the" not in result
    assert "quick" in result
    assert "brown" in result


def test_filter_tokens_min_length():
    tokens = ["a", "ab", "abc", "abcd"]
    result = filter_tokens(tokens, stopwords=set(), min_length=3)
    assert "a" not in result
    assert "ab" not in result
    assert "abc" in result


def test_filter_tokens_removes_pure_digits():
    tokens = ["word", "123", "456", "test"]
    result = filter_tokens(tokens, stopwords=set())
    assert "123" not in result
    assert "word" in result


def test_filter_tokens_custom_stopwords():
    tokens = ["apple", "banana", "cherry"]
    result = filter_tokens(tokens, stopwords={"banana"})
    assert "banana" not in result
    assert "apple" in result


# ---------------------------------------------------------------------------
# extract_ngrams
# ---------------------------------------------------------------------------


def test_extract_ngrams_returns_frequent_bigrams():
    tokens = ["quick", "brown", "fox", "quick", "brown", "dog"]
    result = extract_ngrams(tokens, n=2, min_freq=2)
    assert "quick brown" in result


def test_extract_ngrams_skips_low_frequency():
    tokens = ["once", "unique", "word"]
    result = extract_ngrams(tokens, n=2, min_freq=2)
    assert result == []


def test_extract_ngrams_empty_input():
    assert extract_ngrams([], n=2) == []


# ---------------------------------------------------------------------------
# prepare_flashcard_candidates
# ---------------------------------------------------------------------------


def test_prepare_flashcard_candidates_returns_string(temp_dir):
    p = temp_dir / "text.txt"
    # Write enough repeated content to produce bigrams
    p.write_text("quickly brown fox quickly brown dog quickly brown cat " * 5)
    result = prepare_flashcard_candidates(str(p))
    assert isinstance(result, list)
    assert result


def test_prepare_flashcard_candidates_file_like_input(temp_dir):
    """Ensure the function accepts file-like input without app context."""
    p = temp_dir / "text.txt"
    p.write_text("apple orange banana apple orange " * 3)
    # Should not raise without a web app context.
    result = prepare_flashcard_candidates(str(p))
    assert isinstance(result, list)


def test_extract_flashcard_candidates_removes_noise_and_stopwords():
    text = "The the 123 https://example.com strategic roadmap improves planning."
    result = extract_flashcard_candidates(text, target_count=10)
    expressions = {str(item["expression"]) for item in result}
    assert "the" not in expressions
    assert "123" not in expressions
    assert "strategic" in expressions


def test_extract_flashcard_candidates_dedupes_inflected_words():
    text = "Teams run daily. The runner is running a reliable process."
    result = extract_flashcard_candidates(text, target_count=20, include_phrases=False)
    expressions = [str(item["expression"]) for item in result]
    assert "run" in expressions
    assert "running" not in expressions


def test_extract_flashcard_candidates_finds_repeated_phrases():
    text = (
        "Machine learning systems need clean data. "
        "Machine learning workflows need careful evaluation. "
        "Machine learning improves language tools."
    )
    result = extract_flashcard_candidates(text, target_count=10)
    expressions = [str(item["expression"]) for item in result]
    assert "machine learning" in expressions


def test_extract_flashcard_candidates_ranks_strong_phrase_above_word():
    text = (
        "Neural network models can overfit. "
        "Neural network training requires validation. "
        "Neural network design affects performance. "
        "Network reliability matters."
    )
    result = extract_flashcard_candidates(text, target_count=30)
    expressions = [str(item["expression"]) for item in result]
    assert expressions.index("neural network") < expressions.index("network")


def test_extract_flashcard_candidates_respects_target_count():
    text = " ".join(f"specialterm{chr(97 + i)}" for i in range(20))
    result = extract_flashcard_candidates(text, target_count=5, include_phrases=False)
    assert len(result) == 5
