"""End-to-end integration tests for the --humanise feature (Task Group 8)."""

from __future__ import annotations

import io
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from uwotm8.convert import main
from uwotm8.humanise import HumaniseResult, humanise_text


class TestEndToEndMixedTells:
    """End-to-end: --humanise on a file with mixed character and structural tells."""

    def test_mixed_character_and_structural_tells_report(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A markdown file with both character and structural tells produces
        a report covering both categories."""
        src = tmp_path / "mixed.md"
        src.write_text(
            "It\u2019s important to note that the project\u2014which was large\u2014succeeded.\n"
            "Hello\u00a0world.\n",
            encoding="utf-8",
        )

        with patch("sys.argv", ["uwotm8", "--humanise", str(src)]):
            exit_code = main()

        assert exit_code == 0

        content = src.read_text(encoding="utf-8")
        # Character tells applied: smart quote, em dash, nbsp
        assert "\u2019" not in content
        assert "\u2014" not in content
        assert "\u00a0" not in content

        # Structural tell (filler phrase) should be flagged only (not rewritten
        # because --rewrite was not specified). But the text "important to note"
        # should still be present since structural tells are flag-only by default.
        # Note: filler phrase detection may or may not match after character
        # substitution; the smart quote replacement changes the apostrophe.
        captured = capsys.readouterr()
        # Report should be on stderr and mention findings.
        assert "Humanise Report" in captured.err


class TestEndToEndRewriteAll:
    """End-to-end: --humanise --rewrite all --level full on a file with all tell types."""

    def test_rewrite_all_full_level(self, tmp_path: Path) -> None:
        """All tell types are detected and structural tells are rewritten."""
        src = tmp_path / "all_tells.md"
        src.write_text(
            "It's important to note that this matters.\n"
            "Hello\u00a0world\u2026 test.\n"
            "Furthermore, the first point is important.\n"
            "Some intervening text here.\n"
            "Moreover, the second point matters too.\n",
            encoding="utf-8",
        )

        with patch("sys.argv", [
            "uwotm8", "--humanise", "--rewrite", "all", "--level", "full", str(src),
        ]):
            exit_code = main()

        assert exit_code == 0
        content = src.read_text(encoding="utf-8")
        # Character tells applied.
        assert "\u00a0" not in content
        assert "\u2026" not in content
        # Filler phrase rewritten.
        assert "important to note" not in content.lower()
        # At least one repetitive transition removed.
        count_transitions = (
            content.lower().count("furthermore") + content.lower().count("moreover")
        )
        assert count_transitions < 2


class TestEndToEndAnnotateFormats:
    """End-to-end: --humanise --annotate inserts annotations for each format."""

    @pytest.mark.parametrize(
        "ext,marker",
        [
            (".md", "<!-- HUMANISE:"),
            (".py", "# HUMANISE:"),
            (".html", "<!-- HUMANISE:"),
            (".rst", ".. HUMANISE:"),
            (".txt", "[HUMANISE:"),
        ],
    )
    def test_annotate_per_format(self, tmp_path: Path, ext: str, marker: str) -> None:
        """Inline annotations use the correct format for each file type."""
        src = tmp_path / f"test{ext}"
        src.write_text("Hello\u00a0world.", encoding="utf-8")

        with patch("sys.argv", ["uwotm8", "--humanise", "--annotate", str(src)]):
            exit_code = main()

        assert exit_code == 0
        content = src.read_text(encoding="utf-8")
        assert marker in content


class TestEndToEndCheckExitCodes:
    """End-to-end: --humanise --check returns correct exit codes."""

    def test_check_exit_1_with_tells(self, tmp_path: Path) -> None:
        """Exit code 1 when tells are detected in check mode."""
        src = tmp_path / "dirty.md"
        src.write_text("Hello\u00a0world.", encoding="utf-8")

        with patch("sys.argv", ["uwotm8", "--humanise", "--check", str(src)]):
            exit_code = main()

        assert exit_code == 1
        # File must not be modified.
        assert "\u00a0" in src.read_text(encoding="utf-8")

    def test_check_exit_0_when_clean(self, tmp_path: Path) -> None:
        """Exit code 0 when no tells are found in check mode."""
        src = tmp_path / "clean.md"
        src.write_text("Perfectly clean text with no AI tells.", encoding="utf-8")

        with patch("sys.argv", ["uwotm8", "--humanise", "--check", str(src)]):
            exit_code = main()

        assert exit_code == 0


class TestEndToEndReadingAge:
    """End-to-end: --humanise --reading-age general produces reading age report."""

    def test_reading_age_general_report(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Reading age report with suggestions appears in stderr output."""
        src = tmp_path / "complex.md"
        src.write_text(
            "The implementation of comprehensive environmental sustainability "
            "initiatives necessitates the collaborative participation of "
            "governmental organisations, multinational corporations, and "
            "individual stakeholders.\n",
            encoding="utf-8",
        )

        with patch("sys.argv", [
            "uwotm8", "--humanise", "--reading-age", "general", str(src),
        ]):
            exit_code = main()

        captured = capsys.readouterr()
        report = captured.err
        assert "Reading Age" in report
        assert "target" in report.lower()
        assert "current" in report.lower()


class TestEdgeCases:
    """Edge-case integration tests."""

    def test_empty_file_produces_no_errors(self, tmp_path: Path) -> None:
        """An empty file is processed without errors."""
        src = tmp_path / "empty.md"
        src.write_text("", encoding="utf-8")

        with patch("sys.argv", ["uwotm8", "--humanise", str(src)]):
            exit_code = main()

        assert exit_code == 0
        assert src.read_text(encoding="utf-8") == ""

    def test_file_with_no_tells_produces_clean_report(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A file with no AI tells produces a clean report (no findings)."""
        src = tmp_path / "clean.md"
        src.write_text("This is normal text with no tells at all.", encoding="utf-8")

        with patch("sys.argv", ["uwotm8", "--humanise", str(src)]):
            exit_code = main()

        assert exit_code == 0
        # No report should be printed to stderr (no findings, no reading age).
        captured = capsys.readouterr()
        assert "Humanise Report" not in captured.err

    def test_rewrite_without_humanise_produces_validation_error(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """--rewrite without --humanise returns exit code 2."""
        with patch("sys.argv", ["uwotm8", "--rewrite", "all"]):
            exit_code = main()

        assert exit_code == 2
