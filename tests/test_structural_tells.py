"""Tests for structural tell detection and rewriting (Task Group 3)."""

from __future__ import annotations

from uwotm8.humanise import humanise_text


class TestFillerPhraseDetection:
    """Test filler phrase detection in flagging mode."""

    def test_filler_phrase_flagged_without_rewrite(self) -> None:
        """Filler phrases are flagged but text is not modified when rewrite is None."""
        text = "It's important to note that the project succeeded."
        result = humanise_text(text, level="moderate", rewrite=None)
        # Text should NOT be modified (structural tells are flag-only by default).
        assert result.text == text
        filler_findings = [f for f in result.findings if f["tell_name"] == "filler_phrases"]
        assert len(filler_findings) == 1
        assert filler_findings[0]["line_number"] == 1

    def test_filler_phrase_rewritten_when_rewrite_includes_option(self) -> None:
        """Filler phrases are removed when rewrite includes 'filler-phrases'."""
        text = "It's important to note that the project succeeded."
        result = humanise_text(text, level="moderate", rewrite=["filler-phrases"])
        assert "It's important to note that" not in result.text
        # The remaining text should start with a capital letter.
        assert result.text[0].isupper()

    def test_filler_phrase_rewritten_with_rewrite_all(self) -> None:
        """Filler phrases are removed when rewrite includes 'all'."""
        text = "In today's world, technology is everywhere."
        result = humanise_text(text, level="moderate", rewrite=["all"])
        assert "In today's world," not in result.text
        assert "technology" in result.text.lower()


class TestHedgingLanguageDetection:
    """Test hedging language detection and rewriting."""

    def test_hedging_language_flagged_without_rewrite(self) -> None:
        """Hedging language is flagged but text is not modified when rewrite is None."""
        text = "It's worth noting that the results were positive."
        result = humanise_text(text, level="moderate", rewrite=None)
        assert result.text == text
        hedging_findings = [f for f in result.findings if f["tell_name"] == "hedging_language"]
        assert len(hedging_findings) == 1

    def test_hedging_language_rewritten(self) -> None:
        """Hedging language is removed when rewrite includes 'hedging'."""
        text = "Arguably, this is the best approach."
        result = humanise_text(text, level="moderate", rewrite=["hedging"])
        assert "Arguably," not in result.text
        assert result.text[0].isupper()


class TestBulletListDetection:
    """Test bullet-list-after-single-sentence detection."""

    def test_bullet_list_after_sentence_detected(self) -> None:
        """A single sentence followed by bullet list is detected at full tier."""
        text = (
            "The project has several key benefits.\n"
            "- Improved performance\n"
            "- Better reliability\n"
            "- Lower costs\n"
        )
        result = humanise_text(text, level="full", rewrite=None)
        bullet_findings = [
            f for f in result.findings if f["tell_name"] == "bullet_list_after_single_sentence"
        ]
        assert len(bullet_findings) >= 1

    def test_bullet_list_rewritten_to_prose(self) -> None:
        """Bullet list is restructured into flowing prose when rewrite includes 'bullet-lists'."""
        text = (
            "The project has several key benefits.\n"
            "- Improved performance\n"
            "- Better reliability\n"
            "- Lower costs\n"
        )
        result = humanise_text(text, level="full", rewrite=["bullet-lists"])
        # The bullet markers should be gone.
        assert "\n-" not in result.text or "\n- " not in result.text


class TestUniformParagraphDetection:
    """Test uniform paragraph length detection."""

    def test_uniform_paragraph_length_flagged(self) -> None:
        """Uniform paragraph lengths are flagged at full tier."""
        # Create three paragraphs of similar length separated by blank lines.
        para = "This is a paragraph that contains roughly the same number of characters as each other paragraph here."
        text = f"{para}\n\n{para}\n\n{para}"
        result = humanise_text(text, level="full", rewrite=None)
        uniform_findings = [
            f for f in result.findings if f["tell_name"] == "uniform_paragraph_length"
        ]
        assert len(uniform_findings) >= 1
        # Text should not be modified (flag-only).
        assert result.text == text


class TestRepetitiveTransitionDetection:
    """Test repetitive transition word detection."""

    def test_repetitive_transitions_flagged(self) -> None:
        """Sequential use of Furthermore/Moreover/Additionally is flagged at full tier."""
        text = (
            "Furthermore, the first point is important.\n"
            "Some intervening text here.\n"
            "Moreover, the second point matters too.\n"
        )
        result = humanise_text(text, level="full", rewrite=None)
        transition_findings = [
            f for f in result.findings if f["tell_name"] == "repetitive_transitions"
        ]
        assert len(transition_findings) >= 1
        # Text should not be modified (flag-only).
        assert result.text == text

    def test_repetitive_transitions_rewritten(self) -> None:
        """Repetitive transitions are varied or removed when rewrite includes the option."""
        text = (
            "Furthermore, the first point is important.\n"
            "Some intervening text here.\n"
            "Moreover, the second point matters too.\n"
        )
        result = humanise_text(text, level="full", rewrite=["repetitive-transitions"])
        # At least one of the transition words should be removed or changed.
        original_count = text.lower().count("furthermore") + text.lower().count("moreover")
        result_count = result.text.lower().count("furthermore") + result.text.lower().count("moreover")
        assert result_count < original_count


class TestStructuralTellsFlagOnlyDefault:
    """Test that structural tells are flag-only when rewrite is None."""

    def test_structural_tells_do_not_modify_text_without_rewrite(self) -> None:
        """All structural tells leave text unchanged when rewrite is None."""
        text = (
            "It's important to note that testing is crucial.\n"
            "Arguably, this is the best approach.\n"
        )
        result = humanise_text(text, level="moderate", rewrite=None)
        # Text should be unchanged (character-level tells may apply but there
        # are no character-level tells in this text at moderate tier).
        assert result.text == text
        # But findings should be recorded.
        structural_findings = [
            f
            for f in result.findings
            if f["tell_name"] in ("filler_phrases", "hedging_language")
        ]
        assert len(structural_findings) >= 1
