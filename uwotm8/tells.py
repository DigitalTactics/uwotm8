"""AI tell definitions registry for the humanise feature.

This module contains the data model and registry of AI-generated text
patterns ("tells") that can be detected and optionally rewritten. Each
tell is a dataclass instance appended to the module-level ``TELLS``
list. Adding a new tell requires only appending a new ``Tell`` instance
-- no other code changes are needed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Pattern, Union


class TellCategory(Enum):
    """Category of an AI tell.

    Attributes:
        CHARACTER: Character-level normalisation (e.g. smart quotes, em dashes).
        STRUCTURAL: Structural pattern (e.g. filler phrases, bullet lists).
    """

    CHARACTER = "character"
    STRUCTURAL = "structural"


class TellTier(Enum):
    """Aggressiveness tier for tell detection and replacement.

    Tiers are cumulative: *minimal* is a subset of *moderate*, which is a
    subset of *full*.

    Attributes:
        MINIMAL: Safe for all content types including scientific text.
        MODERATE: Default tier; adds formatting and common phrase tells.
        FULL: Includes structural pattern detection and rewriting.
    """

    MINIMAL = "minimal"
    MODERATE = "moderate"
    FULL = "full"


# Ordered list used by ``get_tells_for_tier`` to determine cumulative
# inclusion.  Index position encodes severity: lower index = less
# aggressive.
_TIER_ORDER: list[TellTier] = [TellTier.MINIMAL, TellTier.MODERATE, TellTier.FULL]


@dataclass(frozen=True)
class Tell:
    """A single AI tell definition.

    Attributes:
        name: Short machine-friendly identifier (e.g. ``"non_breaking_space"``).
        category: Whether this is a character-level or structural tell.
        pattern: A compiled regex *or* a callable that accepts text and
            returns an iterable of ``re.Match``-like objects.
        replacement: A literal replacement string, a callable that
            receives a ``re.Match`` and returns a string, or ``None``
            when the tell is flagging-only.
        description: Human-readable explanation shown in reports.
        tier: The aggressiveness tier at which this tell is active.
    """

    name: str
    category: TellCategory
    pattern: Union[Pattern[str], Callable[[str], list[re.Match[str]]]]
    replacement: Union[str, Callable[[re.Match[str]], str], None]
    description: str
    tier: TellTier


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TELLS: list[Tell] = []

# ---- Character-level tells (minimal tier) --------------------------------

TELLS.append(
    Tell(
        name="non_breaking_space",
        category=TellCategory.CHARACTER,
        pattern=re.compile(r"\u00A0"),
        replacement=" ",
        description="Non-breaking space replaced with normal space.",
        tier=TellTier.MINIMAL,
    )
)

TELLS.append(
    Tell(
        name="zero_width_chars",
        category=TellCategory.CHARACTER,
        pattern=re.compile(r"[\u200B\u200C\u200D\uFEFF]"),
        replacement="",
        description="Zero-width character removed.",
        tier=TellTier.MINIMAL,
    )
)

TELLS.append(
    Tell(
        name="smart_double_quotes",
        category=TellCategory.CHARACTER,
        pattern=re.compile(r"[\u201C\u201D]"),
        replacement='"',
        description="Smart double quote replaced with straight double quote.",
        tier=TellTier.MINIMAL,
    )
)

TELLS.append(
    Tell(
        name="smart_single_quotes",
        category=TellCategory.CHARACTER,
        pattern=re.compile(r"[\u2018\u2019]"),
        replacement="'",
        description="Smart single quote replaced with straight single quote.",
        tier=TellTier.MINIMAL,
    )
)

TELLS.append(
    Tell(
        name="unicode_ellipsis",
        category=TellCategory.CHARACTER,
        pattern=re.compile(r"\u2026"),
        replacement="...",
        description="Unicode ellipsis replaced with three periods.",
        tier=TellTier.MINIMAL,
    )
)

# ---- Character-level tells (moderate tier) --------------------------------

TELLS.append(
    Tell(
        name="em_dash",
        category=TellCategory.CHARACTER,
        pattern=re.compile(r"\s*\u2014\s*"),
        replacement=", ",
        description="Em dash replaced with comma.",
        tier=TellTier.MODERATE,
    )
)

TELLS.append(
    Tell(
        name="en_dash",
        category=TellCategory.CHARACTER,
        pattern=re.compile(r"(?<=\d)\u2013(?=\d)"),
        replacement="-",
        description="En dash between numbers replaced with hyphen.",
        tier=TellTier.MODERATE,
    )
)

TELLS.append(
    Tell(
        name="excessive_bold_markdown",
        category=TellCategory.CHARACTER,
        pattern=re.compile(r"\*\*(.+?)\*\*"),
        replacement=r"\1",
        description="Excessive bold markdown formatting stripped.",
        tier=TellTier.MODERATE,
    )
)

TELLS.append(
    Tell(
        name="excessive_italic_markdown",
        category=TellCategory.CHARACTER,
        pattern=re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)"),
        replacement=r"\1",
        description="Excessive italic markdown formatting stripped.",
        tier=TellTier.MODERATE,
    )
)

TELLS.append(
    Tell(
        name="fancy_unicode_bullets",
        category=TellCategory.CHARACTER,
        pattern=re.compile(r"^[\u2022\u2023\u25E6\u2043\u2219]", re.MULTILINE),
        replacement="-",
        description="Fancy Unicode bullet replaced with plain hyphen.",
        tier=TellTier.MODERATE,
    )
)

# ---- Structural tells (moderate tier) -------------------------------------

_FILLER_PHRASES: list[str] = [
    r"It'?s important to note that\s*",
    r"In today'?s world,?\s*",
    r"Let'?s dive in(?:\s+to)?\.?\s*",
    r"In this article,?\s*",
    r"When it comes to\s+",
    r"At the end of the day,?\s*",
    r"It goes without saying that\s*",
    r"Needless to say,?\s*",
    r"In conclusion,?\s*",
    r"To summarise,?\s*",
    r"To summarize,?\s*",
]

TELLS.append(
    Tell(
        name="filler_phrases",
        category=TellCategory.STRUCTURAL,
        pattern=re.compile(r"(?i)\b(?:" + "|".join(_FILLER_PHRASES) + r")", re.MULTILINE),
        replacement="",
        description="Filler phrase detected.",
        tier=TellTier.MODERATE,
    )
)

_HEDGING_PHRASES: list[str] = [
    r"It'?s worth noting that\s*",
    r"It is worth noting that\s*",
    r"(?:A|a)rguably,?\s*",
    r"(?:O|o)ne might say that\s*",
    r"(?:O|o)ne could argue that\s*",
    r"(?:I|i)t can be said that\s*",
    r"(?:I|i)n a sense,?\s*",
    r"(?:T|t)o some extent,?\s*",
    r"(?:I|i)t should be noted that\s*",
]

TELLS.append(
    Tell(
        name="hedging_language",
        category=TellCategory.STRUCTURAL,
        pattern=re.compile(r"(?:" + "|".join(_HEDGING_PHRASES) + r")", re.MULTILINE),
        replacement="",
        description="Hedging language detected.",
        tier=TellTier.MODERATE,
    )
)

# ---- Structural tells (full tier) -----------------------------------------

TELLS.append(
    Tell(
        name="bullet_list_after_single_sentence",
        category=TellCategory.STRUCTURAL,
        pattern=re.compile(
            r"^[^\n]+[.!?]\s*\n(?:\s*[-*]\s+[^\n]+\n?){2,}",
            re.MULTILINE,
        ),
        replacement=None,
        description="Single sentence followed by bullet list detected.",
        tier=TellTier.FULL,
    )
)

TELLS.append(
    Tell(
        name="uniform_paragraph_length",
        category=TellCategory.STRUCTURAL,
        pattern=re.compile(
            # Matches a sequence of 3+ paragraphs separated by blank lines
            # where each paragraph is roughly the same length.  Actual
            # uniformity checking is best done via a callable; this regex
            # captures candidate paragraph blocks.
            r"(?:^.{40,}\n\n){2,}.{40,}$",
            re.MULTILINE,
        ),
        replacement=None,
        description="Uniform paragraph length detected -- consider varying paragraph sizes.",
        tier=TellTier.FULL,
    )
)

TELLS.append(
    Tell(
        name="repetitive_transitions",
        category=TellCategory.STRUCTURAL,
        pattern=re.compile(
            r"(?:^|\n)\s*(?:Furthermore|Moreover|Additionally)\b[^\n]*\n"
            r"(?:.*\n)*?"
            r"\s*(?:Furthermore|Moreover|Additionally)\b",
            re.MULTILINE,
        ),
        replacement=None,
        description="Repetitive transition words detected (Furthermore/Moreover/Additionally in sequence).",
        tier=TellTier.FULL,
    )
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def get_tells_for_tier(tier: TellTier) -> list[Tell]:
    """Return all tells at or below the given tier.

    Tiers are cumulative:
    - ``MINIMAL`` returns only minimal tells.
    - ``MODERATE`` returns minimal + moderate tells.
    - ``FULL`` returns all tells.

    Args:
        tier: The maximum tier to include.

    Returns:
        A list of ``Tell`` instances whose tier is at or below *tier*.
    """
    max_index = _TIER_ORDER.index(tier)
    allowed_tiers = set(_TIER_ORDER[: max_index + 1])
    return [t for t in TELLS if t.tier in allowed_tiers]
