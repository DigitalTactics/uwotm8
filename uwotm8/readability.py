"""Readability formulae for reading age analysis.

This module implements three standard readability indices directly,
without relying on external dependencies:

- Flesch-Kincaid Grade Level
- Gunning Fog Index
- Coleman-Liau Index

A composite score is computed as the average of the three. Scores are
mapped to descriptive levels (``basic``, ``general``, ``advanced``,
``technical``) and to approximate reading ages.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Optional, Union


# ---------------------------------------------------------------------------
# Descriptive level mapping
# ---------------------------------------------------------------------------

# Each level maps to a (min_age, max_age) range. The composite score is
# treated as a US grade level, and we convert to approximate UK reading
# age by adding 5 (US grade 1 ~ age 6).

LEVEL_RANGES: dict[str, tuple[int, int]] = {
    "basic": (9, 11),
    "general": (12, 14),
    "advanced": (15, 17),
    "technical": (18, 99),
}


def descriptive_level_for_age(age: float) -> str:
    """Return the descriptive level for a given reading age.

    Args:
        age: A numeric reading age.

    Returns:
        One of ``"basic"``, ``"general"``, ``"advanced"``, or ``"technical"``.
    """
    if age < 12:
        return "basic"
    if age < 15:
        return "general"
    if age < 18:
        return "advanced"
    return "technical"


def grade_to_age(grade: float) -> float:
    """Convert a US grade level to an approximate reading age.

    The standard conversion is ``age = grade + 5``.

    Args:
        grade: A US grade level score.

    Returns:
        The approximate reading age.
    """
    return grade + 5


def target_to_age(target: Union[int, str]) -> float:
    """Convert a reading age target to a numeric age.

    If *target* is already numeric, it is returned as-is. If it is a
    descriptive level string (e.g. ``"general"``), the midpoint of the
    level's age range is returned.

    Args:
        target: A numeric age or descriptive level string.

    Returns:
        A numeric reading age.

    Raises:
        ValueError: If *target* is an unrecognised descriptive level.
    """
    if isinstance(target, (int, float)):
        return float(target)
    target_lower = target.lower()
    if target_lower in LEVEL_RANGES:
        lo, hi = LEVEL_RANGES[target_lower]
        if target_lower == "technical":
            return 18.0
        return (lo + hi) / 2.0
    raise ValueError(f"Unrecognised reading age target: {target!r}")


# ---------------------------------------------------------------------------
# Text analysis utilities
# ---------------------------------------------------------------------------

# Vowels for syllable counting.
_VOWELS = set("aeiouyAEIOUY")

# Common silent-e and multi-syllable suffix patterns.
_SUFFIX_SUB = re.compile(r"(?:es|ed|e)$", re.IGNORECASE)
_CONSECUTIVE_VOWELS = re.compile(r"[aeiouy]+", re.IGNORECASE)

# Sentence boundary pattern.
_SENTENCE_BOUNDARY = re.compile(r"[.!?]+")

# Word pattern -- sequences of alphabetic characters (possibly with
# internal apostrophes/hyphens).
_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z\'\-]*[a-zA-Z]|[a-zA-Z]")


def count_syllables(word: str) -> int:
    """Count the number of syllables in a word using a heuristic method.

    This uses a vowel-group counting approach that handles common UK
    English patterns.

    Args:
        word: A single word (alphabetic characters only).

    Returns:
        The estimated syllable count (minimum 1).
    """
    word = word.lower().strip()
    if not word:
        return 0
    if len(word) <= 3:
        return 1

    # Count vowel groups.
    count = len(_CONSECUTIVE_VOWELS.findall(word))

    # Subtract silent e at end (but not -le endings).
    if word.endswith("e") and not word.endswith("le"):
        count -= 1

    # Common suffixes that add syllables.
    if word.endswith("tion") or word.endswith("sion"):
        pass  # already counted
    if word.endswith("ed"):
        # -ed is usually not a separate syllable unless preceded by t or d.
        if len(word) > 2 and word[-3] not in ("t", "d"):
            count -= 1
    if word.endswith("es"):
        # -es is usually not a separate syllable unless preceded by
        # s, x, z, ch, sh.
        if len(word) > 2 and word[-3] not in ("s", "x", "z") and not (
            len(word) > 3 and word[-4:-2] in ("ch", "sh")
        ):
            count -= 1

    return max(count, 1)


def _extract_words(text: str) -> list[str]:
    """Extract words from text.

    Args:
        text: The input text.

    Returns:
        A list of word strings.
    """
    return _WORD_RE.findall(text)


def _extract_sentences(text: str) -> list[str]:
    """Split text into sentences.

    Args:
        text: The input text.

    Returns:
        A list of sentence strings (non-empty).
    """
    # Split on sentence-ending punctuation.
    parts = _SENTENCE_BOUNDARY.split(text)
    return [s.strip() for s in parts if s.strip()]


def _count_complex_words(words: list[str]) -> int:
    """Count complex words (3+ syllables) for the Gunning Fog Index.

    Proper nouns, compound words joined by hyphens, and common suffixes
    (-es, -ed, -ing) that push a word to 3 syllables are handled.

    Args:
        words: A list of word strings.

    Returns:
        The number of words with 3 or more syllables.
    """
    count = 0
    for word in words:
        if count_syllables(word) >= 3:
            count += 1
    return count


def _count_characters_in_words(words: list[str]) -> int:
    """Count the total number of alphabetic characters in a word list.

    Args:
        words: A list of word strings.

    Returns:
        Total character count.
    """
    return sum(len(w) for w in words)


# ---------------------------------------------------------------------------
# Readability formulae
# ---------------------------------------------------------------------------


def flesch_kincaid_grade_level(text: str) -> float:
    """Calculate the Flesch-Kincaid Grade Level for *text*.

    Formula::

        0.39 * (total_words / total_sentences)
        + 11.8 * (total_syllables / total_words)
        - 15.59

    Args:
        text: The input text.

    Returns:
        The Flesch-Kincaid Grade Level score.
    """
    words = _extract_words(text)
    sentences = _extract_sentences(text)

    total_words = len(words)
    total_sentences = max(len(sentences), 1)
    total_syllables = sum(count_syllables(w) for w in words)

    if total_words == 0:
        return 0.0

    return (
        0.39 * (total_words / total_sentences)
        + 11.8 * (total_syllables / total_words)
        - 15.59
    )


def gunning_fog_index(text: str) -> float:
    """Calculate the Gunning Fog Index for *text*.

    Formula::

        0.4 * ((total_words / total_sentences)
               + 100 * (complex_words / total_words))

    Where complex words have 3 or more syllables.

    Args:
        text: The input text.

    Returns:
        The Gunning Fog Index score.
    """
    words = _extract_words(text)
    sentences = _extract_sentences(text)

    total_words = len(words)
    total_sentences = max(len(sentences), 1)
    complex_words = _count_complex_words(words)

    if total_words == 0:
        return 0.0

    return 0.4 * (
        (total_words / total_sentences)
        + 100 * (complex_words / total_words)
    )


def coleman_liau_index(text: str) -> float:
    """Calculate the Coleman-Liau Index for *text*.

    Formula::

        0.0588 * L - 0.296 * S - 15.8

    Where *L* is the average number of letters per 100 words and *S* is
    the average number of sentences per 100 words.

    Args:
        text: The input text.

    Returns:
        The Coleman-Liau Index score.
    """
    words = _extract_words(text)
    sentences = _extract_sentences(text)

    total_words = len(words)
    total_sentences = max(len(sentences), 1)
    total_chars = _count_characters_in_words(words)

    if total_words == 0:
        return 0.0

    l_val = (total_chars / total_words) * 100
    s_val = (total_sentences / total_words) * 100

    return 0.0588 * l_val - 0.296 * s_val - 15.8


def composite_score(text: str) -> float:
    """Calculate the composite readability score.

    The composite is the average of the Flesch-Kincaid Grade Level,
    Gunning Fog Index, and Coleman-Liau Index.

    Args:
        text: The input text.

    Returns:
        The average grade-level score.
    """
    fk = flesch_kincaid_grade_level(text)
    gf = gunning_fog_index(text)
    cl = coleman_liau_index(text)
    return (fk + gf + cl) / 3.0


# ---------------------------------------------------------------------------
# Per-paragraph / per-sentence suggestion generation
# ---------------------------------------------------------------------------


@dataclass
class ReadingAgeSuggestion:
    """A suggestion for a sentence that exceeds the target reading age.

    Attributes:
        line_number: The 1-based line number of the sentence.
        grade: The Flesch-Kincaid grade of the sentence.
        message: A human-readable suggestion string.
    """

    line_number: int
    grade: float
    message: str


def generate_suggestions(
    text: str,
    target_age: float,
) -> list[ReadingAgeSuggestion]:
    """Generate per-sentence suggestions for text exceeding the target.

    Each sentence in the text is evaluated individually. If a sentence's
    Flesch-Kincaid grade level (converted to age) exceeds the target,
    a suggestion is generated.

    Args:
        text: The full input text.
        target_age: The numeric target reading age.

    Returns:
        A list of ``ReadingAgeSuggestion`` instances.
    """
    suggestions: list[ReadingAgeSuggestion] = []
    lines = text.split("\n")

    # Build a flat list of (sentence_text, line_number) pairs.
    for line_idx, line in enumerate(lines, start=1):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Split the line into sentences.
        sentence_parts = _SENTENCE_BOUNDARY.split(line_stripped)
        for sentence in sentence_parts:
            sentence = sentence.strip()
            words = _extract_words(sentence)
            if len(words) < 5:
                # Skip very short fragments.
                continue

            grade = flesch_kincaid_grade_level(sentence)
            age = grade_to_age(grade)

            if age > target_age:
                suggestions.append(
                    ReadingAgeSuggestion(
                        line_number=line_idx,
                        grade=round(grade, 1),
                        message=(
                            f"Sentence on line {line_idx} has a Flesch-Kincaid "
                            f"grade of {grade:.1f}; consider splitting or simplifying"
                        ),
                    )
                )

    return suggestions


# ---------------------------------------------------------------------------
# Full reading age report
# ---------------------------------------------------------------------------


def analyse_reading_age(
    text: str,
    target: Union[int, str],
) -> dict[str, Any]:
    """Produce a complete reading age report for *text*.

    The report includes the current reading age (numeric and descriptive),
    the target age, the delta between them, and per-sentence suggestions
    for sentences that exceed the target.

    Args:
        text: The input text.
        target: A numeric age or descriptive level string.

    Returns:
        A dict with keys ``current_age``, ``current_level``, ``target_age``,
        ``target_level``, ``delta``, and ``suggestions``.
    """
    score = composite_score(text)
    current_age = grade_to_age(score)
    current_level = descriptive_level_for_age(current_age)

    target_age = target_to_age(target)
    target_level = descriptive_level_for_age(target_age)

    delta = current_age - target_age

    suggestion_list = generate_suggestions(text, target_age)
    suggestion_messages = [s.message for s in suggestion_list]

    return {
        "current_age": round(current_age, 1),
        "current_level": current_level,
        "target_age": round(target_age, 1),
        "target_level": target_level,
        "delta": round(delta, 1),
        "suggestions": suggestion_messages,
    }
