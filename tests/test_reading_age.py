"""Tests for reading age calculation and suggestions (Task Group 4)."""

from __future__ import annotations

import math

from uwotm8.readability import (
    analyse_reading_age,
    coleman_liau_index,
    composite_score,
    count_syllables,
    descriptive_level_for_age,
    flesch_kincaid_grade_level,
    generate_suggestions,
    grade_to_age,
    gunning_fog_index,
    target_to_age,
)
from uwotm8.humanise import humanise_text


# Reference text: simple prose at approximately a 6th-8th grade reading level.
_SIMPLE_TEXT = (
    "The cat sat on the mat. It was a warm day. "
    "The sun was bright and the sky was blue. "
    "Children played in the park nearby."
)

# Reference text: more complex, higher grade level.
_COMPLEX_TEXT = (
    "The implementation of comprehensive environmental sustainability "
    "initiatives necessitates the collaborative participation of "
    "governmental organisations, multinational corporations, and "
    "individual stakeholders. Furthermore, the establishment of "
    "regulatory frameworks that simultaneously incentivise innovation "
    "while mitigating deleterious ecological consequences represents "
    "a fundamentally challenging proposition."
)


class TestFleschKincaidGradeLevel:
    """Test Flesch-Kincaid Grade Level calculation on known text."""

    def test_simple_text_produces_low_grade(self) -> None:
        """Simple text should produce a low grade level (below 8)."""
        grade = flesch_kincaid_grade_level(_SIMPLE_TEXT)
        assert grade < 8.0, f"Expected grade < 8, got {grade}"

    def test_complex_text_produces_high_grade(self) -> None:
        """Complex text should produce a higher grade level (above 10)."""
        grade = flesch_kincaid_grade_level(_COMPLEX_TEXT)
        assert grade > 10.0, f"Expected grade > 10, got {grade}"

    def test_empty_text_returns_zero(self) -> None:
        """Empty text should return 0."""
        grade = flesch_kincaid_grade_level("")
        assert grade == 0.0


class TestGunningFogIndex:
    """Test Gunning Fog Index calculation on known text."""

    def test_simple_text_produces_low_fog(self) -> None:
        """Simple text should produce a low Fog index."""
        fog = gunning_fog_index(_SIMPLE_TEXT)
        assert fog < 10.0, f"Expected fog < 10, got {fog}"

    def test_complex_text_produces_high_fog(self) -> None:
        """Complex text should produce a higher Fog index."""
        fog = gunning_fog_index(_COMPLEX_TEXT)
        assert fog > 12.0, f"Expected fog > 12, got {fog}"


class TestColemanLiauIndex:
    """Test Coleman-Liau Index calculation on known text."""

    def test_simple_text_produces_low_index(self) -> None:
        """Simple text should produce a low Coleman-Liau index."""
        cli = coleman_liau_index(_SIMPLE_TEXT)
        assert cli < 8.0, f"Expected CLI < 8, got {cli}"

    def test_complex_text_produces_high_index(self) -> None:
        """Complex text with long words should produce a high index."""
        cli = coleman_liau_index(_COMPLEX_TEXT)
        assert cli > 10.0, f"Expected CLI > 10, got {cli}"


class TestCompositeScoreAndDescriptiveLevel:
    """Test composite score averaging and descriptive level mapping."""

    def test_composite_is_average_of_three(self) -> None:
        """Composite score should be the average of the three formulae."""
        fk = flesch_kincaid_grade_level(_SIMPLE_TEXT)
        fog = gunning_fog_index(_SIMPLE_TEXT)
        cli = coleman_liau_index(_SIMPLE_TEXT)
        comp = composite_score(_SIMPLE_TEXT)
        expected = (fk + fog + cli) / 3.0
        assert math.isclose(comp, expected, rel_tol=1e-9)

    def test_basic_level_mapping(self) -> None:
        """Ages 9-11 should map to 'basic'."""
        assert descriptive_level_for_age(9) == "basic"
        assert descriptive_level_for_age(11) == "basic"

    def test_general_level_mapping(self) -> None:
        """Ages 12-14 should map to 'general'."""
        assert descriptive_level_for_age(12) == "general"
        assert descriptive_level_for_age(14) == "general"

    def test_advanced_level_mapping(self) -> None:
        """Ages 15-17 should map to 'advanced'."""
        assert descriptive_level_for_age(15) == "advanced"
        assert descriptive_level_for_age(17) == "advanced"

    def test_technical_level_mapping(self) -> None:
        """Ages 18+ should map to 'technical'."""
        assert descriptive_level_for_age(18) == "technical"
        assert descriptive_level_for_age(25) == "technical"


class TestPerParagraphSuggestions:
    """Test per-paragraph suggestion generation when text exceeds target."""

    def test_complex_text_generates_suggestions_for_low_target(self) -> None:
        """Complex text should generate suggestions when target is low."""
        suggestions = generate_suggestions(_COMPLEX_TEXT, target_age=10.0)
        assert len(suggestions) > 0
        for s in suggestions:
            assert "consider splitting or simplifying" in s.message
            assert s.line_number >= 1

    def test_simple_text_generates_no_suggestions_for_high_target(self) -> None:
        """Simple text should generate no suggestions when target is high."""
        suggestions = generate_suggestions(_SIMPLE_TEXT, target_age=20.0)
        assert len(suggestions) == 0

    def test_suggestion_format_includes_line_number_and_grade(self) -> None:
        """Suggestion messages should include line number and grade."""
        suggestions = generate_suggestions(_COMPLEX_TEXT, target_age=10.0)
        assert len(suggestions) > 0
        msg = suggestions[0].message
        assert "Sentence on line" in msg
        assert "Flesch-Kincaid grade of" in msg


class TestNumericAndDescriptiveTarget:
    """Test that numeric and descriptive targets both work."""

    def test_numeric_target(self) -> None:
        """A numeric target (e.g. 14) should be accepted."""
        age = target_to_age(14)
        assert age == 14.0

    def test_descriptive_target_general(self) -> None:
        """Descriptive target 'general' should map to midpoint of 12-14."""
        age = target_to_age("general")
        assert age == 13.0

    def test_descriptive_target_basic(self) -> None:
        """Descriptive target 'basic' should map to midpoint of 9-11."""
        age = target_to_age("basic")
        assert age == 10.0

    def test_descriptive_target_technical(self) -> None:
        """Descriptive target 'technical' should map to 18."""
        age = target_to_age("technical")
        assert age == 18.0

    def test_analyse_reading_age_with_numeric_target(self) -> None:
        """analyse_reading_age should work with a numeric target."""
        report = analyse_reading_age(_COMPLEX_TEXT, 14)
        assert "current_age" in report
        assert "target_age" in report
        assert report["target_age"] == 14.0
        assert "delta" in report
        assert "suggestions" in report

    def test_analyse_reading_age_with_descriptive_target(self) -> None:
        """analyse_reading_age should work with a descriptive target."""
        report = analyse_reading_age(_COMPLEX_TEXT, "general")
        assert report["target_age"] == 13.0
        assert report["target_level"] == "general"
        assert "current_level" in report


class TestHumaniseIntegration:
    """Test that reading age is integrated into humanise_text."""

    def test_reading_age_report_populated_when_target_provided(self) -> None:
        """humanise_text should populate reading_age_report when target given."""
        result = humanise_text(_COMPLEX_TEXT, reading_age_target=14)
        assert result.reading_age_report is not None
        assert "current_age" in result.reading_age_report
        assert "target_age" in result.reading_age_report
        assert "delta" in result.reading_age_report
        assert "suggestions" in result.reading_age_report

    def test_reading_age_report_none_without_target(self) -> None:
        """humanise_text should leave reading_age_report as None without target."""
        result = humanise_text(_COMPLEX_TEXT)
        assert result.reading_age_report is None
