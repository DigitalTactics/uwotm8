"""Tests for the AI tells registry (uwotm8.tells)."""

from __future__ import annotations

import re

from uwotm8.tells import (
    TELLS,
    Tell,
    TellCategory,
    TellTier,
    get_tells_for_tier,
)


class TestTellDataclass:
    """Test that the Tell dataclass can be instantiated correctly."""

    def test_instantiate_with_all_required_fields(self) -> None:
        """A Tell can be created with every required field."""
        tell = Tell(
            name="test_tell",
            category=TellCategory.CHARACTER,
            pattern=re.compile(r"foo"),
            replacement="bar",
            description="A test tell.",
            tier=TellTier.MINIMAL,
        )
        assert tell.name == "test_tell"
        assert tell.category is TellCategory.CHARACTER
        assert tell.replacement == "bar"
        assert tell.description == "A test tell."
        assert tell.tier is TellTier.MINIMAL

    def test_tell_with_none_replacement(self) -> None:
        """A Tell can have None replacement for flagging-only tells."""
        tell = Tell(
            name="flag_only",
            category=TellCategory.STRUCTURAL,
            pattern=re.compile(r"baz"),
            replacement=None,
            description="Flagging only.",
            tier=TellTier.FULL,
        )
        assert tell.replacement is None


class TestRegistryFiltering:
    """Test filtering the TELLS registry by category and tier."""

    def test_registry_is_non_empty(self) -> None:
        """The registry contains tells."""
        assert len(TELLS) > 0

    def test_filter_by_category_character(self) -> None:
        """Filtering by CHARACTER category returns only character tells."""
        character_tells = [t for t in TELLS if t.category is TellCategory.CHARACTER]
        assert len(character_tells) > 0
        assert all(t.category is TellCategory.CHARACTER for t in character_tells)

    def test_filter_by_category_structural(self) -> None:
        """Filtering by STRUCTURAL category returns only structural tells."""
        structural_tells = [t for t in TELLS if t.category is TellCategory.STRUCTURAL]
        assert len(structural_tells) > 0
        assert all(t.category is TellCategory.STRUCTURAL for t in structural_tells)

    def test_filter_by_tier_minimal(self) -> None:
        """Minimal tier returns only minimal tells."""
        minimal = get_tells_for_tier(TellTier.MINIMAL)
        assert len(minimal) > 0
        assert all(t.tier is TellTier.MINIMAL for t in minimal)

    def test_filter_by_tier_moderate_includes_minimal(self) -> None:
        """Moderate tier includes all minimal tells plus moderate tells."""
        minimal = get_tells_for_tier(TellTier.MINIMAL)
        moderate = get_tells_for_tier(TellTier.MODERATE)
        assert len(moderate) > len(minimal)
        minimal_names = {t.name for t in minimal}
        moderate_names = {t.name for t in moderate}
        assert minimal_names.issubset(moderate_names)

    def test_filter_by_tier_full_includes_all(self) -> None:
        """Full tier includes every tell in the registry."""
        full = get_tells_for_tier(TellTier.FULL)
        assert len(full) == len(TELLS)


class TestTellPatterns:
    """Test that tell patterns match expected input."""

    def test_non_breaking_space_pattern(self) -> None:
        """Non-breaking space pattern matches NBSP character."""
        tell = next(t for t in TELLS if t.name == "non_breaking_space")
        assert isinstance(tell.pattern, re.Pattern)
        assert tell.pattern.search("hello\u00A0world") is not None
        assert tell.pattern.search("hello world") is None

    def test_smart_double_quotes_pattern(self) -> None:
        """Smart double quotes pattern matches curly double quotes."""
        tell = next(t for t in TELLS if t.name == "smart_double_quotes")
        assert isinstance(tell.pattern, re.Pattern)
        assert tell.pattern.search("\u201CHello\u201D") is not None
        assert tell.pattern.search('"Hello"') is None

    def test_filler_phrase_pattern(self) -> None:
        """Filler phrase pattern matches known AI filler phrases."""
        tell = next(t for t in TELLS if t.name == "filler_phrases")
        assert isinstance(tell.pattern, re.Pattern)
        assert tell.pattern.search("It's important to note that this matters") is not None
        assert tell.pattern.search("The cat sat on the mat") is None

    def test_em_dash_pattern(self) -> None:
        """Em dash pattern matches the em dash character."""
        tell = next(t for t in TELLS if t.name == "em_dash")
        assert isinstance(tell.pattern, re.Pattern)
        assert tell.pattern.search("word\u2014another") is not None
        assert tell.pattern.search("word-another") is None


class TestRegistryExtensibility:
    """Test that adding a new tell requires only appending to the list."""

    def test_append_new_tell(self) -> None:
        """Appending a Tell instance to TELLS makes it available via get_tells_for_tier."""
        original_count = len(TELLS)
        new_tell = Tell(
            name="_test_extensibility",
            category=TellCategory.CHARACTER,
            pattern=re.compile(r"XXXXXX"),
            replacement="YYYYYY",
            description="Test extensibility.",
            tier=TellTier.MINIMAL,
        )
        TELLS.append(new_tell)
        try:
            assert len(TELLS) == original_count + 1
            minimal = get_tells_for_tier(TellTier.MINIMAL)
            assert any(t.name == "_test_extensibility" for t in minimal)
        finally:
            TELLS.remove(new_tell)
