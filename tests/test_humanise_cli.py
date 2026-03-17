"""Tests for CLI integration of the --humanise feature (Task Group 6)."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from uwotm8.convert import main


class TestHumaniseCLIFlags:
    """Test that --humanise CLI flags are parsed and dispatched correctly."""

    def test_humanise_flag_activates_humanisation_no_spelling_conversion(self, tmp_path: Path) -> None:
        """--humanise runs humanisation only, no spelling conversion."""
        # File with an American spelling AND an AI tell (non-breaking space).
        src = tmp_path / "test.md"
        src.write_text("The color\u00a0is nice.", encoding="utf-8")

        with patch("sys.argv", ["uwotm8", "--humanise", str(src)]):
            exit_code = main()

        content = src.read_text(encoding="utf-8")
        # Non-breaking space should be replaced (humanisation ran).
        assert "\u00a0" not in content
        # American spelling "color" should NOT have been converted (no spelling conversion).
        assert "color" in content
        assert exit_code == 0

    def test_humanise_rewrite_all_applies_structural_rewrites(self, tmp_path: Path) -> None:
        """--humanise --rewrite all applies structural rewrites."""
        src = tmp_path / "test.md"
        src.write_text(
            "It's important to note that this matters.\n",
            encoding="utf-8",
        )

        with patch("sys.argv", ["uwotm8", "--humanise", "--rewrite", "all", str(src)]):
            exit_code = main()

        content = src.read_text(encoding="utf-8")
        # Filler phrase should have been removed.
        assert "important to note" not in content.lower()
        assert exit_code == 0

    def test_humanise_level_minimal_restricts_to_character_only(self, tmp_path: Path) -> None:
        """--humanise --level minimal only applies character-level tells."""
        src = tmp_path / "test.md"
        # Non-breaking space (minimal) + em dash (moderate).
        src.write_text("Hello\u00a0world \u2014 done.", encoding="utf-8")

        with patch("sys.argv", ["uwotm8", "--humanise", "--level", "minimal", str(src)]):
            exit_code = main()

        content = src.read_text(encoding="utf-8")
        # Non-breaking space should be replaced (minimal tier).
        assert "\u00a0" not in content
        # Em dash should remain (moderate tier, not applied at minimal).
        assert "\u2014" in content
        assert exit_code == 0

    def test_humanise_check_returns_exit_code_1_when_tells_found(self, tmp_path: Path) -> None:
        """--humanise --check returns exit code 1 when tells are detected."""
        src = tmp_path / "test.md"
        src.write_text("Hello\u00a0world.", encoding="utf-8")

        with patch("sys.argv", ["uwotm8", "--humanise", "--check", str(src)]):
            exit_code = main()

        # File should NOT have been modified.
        content = src.read_text(encoding="utf-8")
        assert "\u00a0" in content
        assert exit_code == 1

    def test_humanise_check_returns_exit_code_0_when_clean(self, tmp_path: Path) -> None:
        """--humanise --check returns exit code 0 when no tells found."""
        src = tmp_path / "test.md"
        src.write_text("This is perfectly clean text.", encoding="utf-8")

        with patch("sys.argv", ["uwotm8", "--humanise", "--check", str(src)]):
            exit_code = main()

        assert exit_code == 0

    def test_humanise_reading_age_includes_report(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """--humanise --reading-age 14 includes reading age in terminal report."""
        src = tmp_path / "test.md"
        src.write_text(
            "The quick brown fox jumps over the lazy dog. "
            "Simple sentences are easy to read.\n",
            encoding="utf-8",
        )

        with patch("sys.argv", ["uwotm8", "--humanise", "--reading-age", "14", str(src)]):
            exit_code = main()

        captured = capsys.readouterr()
        # The report should mention reading age.
        assert "Reading Age" in captured.err or "Reading Age" in captured.out

    def test_humanise_annotate_inserts_inline_annotations(self, tmp_path: Path) -> None:
        """--humanise --annotate inserts inline annotations in the file."""
        src = tmp_path / "test.md"
        src.write_text("Hello\u00a0world.", encoding="utf-8")

        with patch("sys.argv", ["uwotm8", "--humanise", "--annotate", str(src)]):
            exit_code = main()

        content = src.read_text(encoding="utf-8")
        assert "HUMANISE:" in content
        assert exit_code == 0

    def test_humanise_comments_only_for_py_files(self, tmp_path: Path) -> None:
        """--humanise --comments-only only analyses comments/docstrings in .py files."""
        src = tmp_path / "test.py"
        src.write_text(
            '# A comment with\u00a0non-breaking space\n'
            'x = "string with\u00a0nbsp"\n',
            encoding="utf-8",
        )

        with patch("sys.argv", ["uwotm8", "--humanise", "--comments-only", str(src)]):
            exit_code = main()

        content = src.read_text(encoding="utf-8")
        # The comment non-breaking space should be fixed.
        assert "# A comment with non-breaking space" in content
        # The string literal non-breaking space should remain.
        assert '\u00a0' in content.split("\n")[1]
        assert exit_code == 0

    def test_humanise_stdin_stdout_streaming(self, capsys: pytest.CaptureFixture[str]) -> None:
        """--humanise with no src reads from stdin and writes to stdout."""
        import io

        input_text = "Hello\u00a0world.\n"
        fake_stdin = io.StringIO(input_text)

        with patch("sys.argv", ["uwotm8", "--humanise"]):
            with patch("sys.stdin", fake_stdin):
                exit_code = main()

        captured = capsys.readouterr()
        # stdout should contain the processed text.
        assert "Hello world." in captured.out
        assert "\u00a0" not in captured.out
        assert exit_code == 0


class TestHumaniseCLIValidation:
    """Test CLI flag validation."""

    def test_rewrite_without_humanise_produces_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """--rewrite without --humanise produces a validation error."""
        with patch("sys.argv", ["uwotm8", "--rewrite", "all"]):
            exit_code = main()

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "requires --humanise" in (captured.err + captured.out).lower() or exit_code == 2
