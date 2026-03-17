"""Tests for character-level tell processing (uwotm8.humanise)."""

from __future__ import annotations

from uwotm8.humanise import HumaniseResult, humanise_text


class TestCharacterLevelTells:
    """Test that character-level tells are correctly applied by humanise_text."""

    def test_non_breaking_space_replacement(self) -> None:
        """Non-breaking spaces are replaced with normal spaces."""
        text = "Hello\u00A0world\u00A0again"
        result = humanise_text(text)
        assert "\u00A0" not in result.text
        assert "Hello world again" == result.text

    def test_smart_quote_normalisation_double(self) -> None:
        """Smart double quotes are normalised to straight double quotes."""
        text = "\u201CHello,\u201D she said."
        result = humanise_text(text)
        assert result.text == '"Hello," she said.'

    def test_smart_quote_normalisation_single(self) -> None:
        """Smart single quotes are normalised to straight single quotes."""
        text = "\u2018Hello,\u2019 she said."
        result = humanise_text(text)
        assert result.text == "'Hello,' she said."

    def test_em_dash_replacement_with_comma(self) -> None:
        """Em dashes are replaced with commas at moderate tier."""
        text = "The project\u2014which was large\u2014succeeded."
        result = humanise_text(text, level="moderate")
        assert "\u2014" not in result.text
        assert ", " in result.text

    def test_zero_width_character_removal(self) -> None:
        """Zero-width characters are removed from text."""
        text = "Hello\u200Bworld\u200C\u200D\uFEFF"
        result = humanise_text(text)
        assert result.text == "Helloworld"

    def test_unicode_ellipsis_replacement(self) -> None:
        """Unicode ellipsis is replaced with three periods."""
        text = "Wait for it\u2026 there it is."
        result = humanise_text(text)
        assert result.text == "Wait for it... there it is."

    def test_excessive_bold_markdown_stripping(self) -> None:
        """Excessive bold markdown formatting is stripped at moderate tier."""
        text = "This is **very important** and **also bold**."
        result = humanise_text(text, level="moderate")
        assert result.text == "This is very important and also bold."

    def test_minimal_tier_skips_em_dash_replacement(self) -> None:
        """Minimal tier does not replace em dashes (moderate-tier tell)."""
        text = "The project\u2014which was large\u2014succeeded."
        result = humanise_text(text, level="minimal")
        assert "\u2014" in result.text

    def test_text_unchanged_when_no_tells_present(self) -> None:
        """Text without any AI tells passes through unchanged."""
        text = "This is perfectly normal text with no AI tells."
        result = humanise_text(text)
        assert result.text == text
        assert len(result.findings) == 0


class TestFindingsRecording:
    """Test that findings are recorded with line numbers and excerpts."""

    def test_findings_contain_tell_name(self) -> None:
        """Each finding records the tell name."""
        text = "Hello\u00A0world"
        result = humanise_text(text)
        assert len(result.findings) > 0
        assert result.findings[0]["tell_name"] == "non_breaking_space"

    def test_findings_contain_line_number(self) -> None:
        """Each finding records a line number."""
        text = "Line one\nHello\u00A0world\nLine three"
        result = humanise_text(text)
        nbsp_findings = [f for f in result.findings if f["tell_name"] == "non_breaking_space"]
        assert len(nbsp_findings) == 1
        assert nbsp_findings[0]["line_number"] == 2

    def test_findings_contain_excerpts(self) -> None:
        """Each finding records original and replacement excerpts."""
        text = "Wait\u2026 done."
        result = humanise_text(text)
        assert len(result.findings) > 0
        finding = result.findings[0]
        assert "original" in finding
        assert "replacement" in finding


class TestHumaniseResult:
    """Test the HumaniseResult dataclass structure."""

    def test_result_has_expected_fields(self) -> None:
        """HumaniseResult has text, findings, and reading_age_report."""
        result = humanise_text("Hello world")
        assert isinstance(result, HumaniseResult)
        assert isinstance(result.text, str)
        assert isinstance(result.findings, list)
        assert result.reading_age_report is None
