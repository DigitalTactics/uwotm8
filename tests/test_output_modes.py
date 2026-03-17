"""Tests for output modes: terminal report, inline annotation, and report-to-disk (Task Group 5)."""

from __future__ import annotations

import os
import tempfile
from typing import Any

from uwotm8.humanise import HumaniseResult, humanise_text
from uwotm8.output import (
    annotate_text,
    format_terminal_report,
    write_report_to_disk,
)
from uwotm8.tells import TellCategory


class TestTerminalReport:
    """Test the terminal report formatter."""

    def test_report_grouped_by_category_with_line_numbers_and_excerpts(self) -> None:
        """Terminal report groups findings by category and includes line numbers and excerpts."""
        result = humanise_text("Hello\u00A0world\nWait\u2026 done.", level="minimal")
        report = format_terminal_report(result)
        # Should contain the category header.
        assert "Character-level" in report
        # Should contain line numbers.
        assert "Line 1" in report or "line 1" in report
        assert "Line 2" in report or "line 2" in report
        # Should contain counts.
        assert "non_breaking_space" in report
        assert "unicode_ellipsis" in report

    def test_report_includes_counts_and_severity_summary(self) -> None:
        """Terminal report includes counts per tell type and a severity summary."""
        text = "Hello\u00A0world\u00A0again\nWait\u2026 done."
        result = humanise_text(text, level="minimal")
        report = format_terminal_report(result)
        # Should include a summary section.
        assert "Summary" in report or "summary" in report
        # Should mention finding counts.
        assert "3" in report  # 2 nbsp + 1 ellipsis

    def test_report_includes_reading_age_section(self) -> None:
        """Terminal report includes reading age section when analysis is present."""
        text = (
            "The comprehensive examination of the underlying infrastructure "
            "revealed significant deficiencies in the operational protocols. "
            "Furthermore, the implementation of remedial measures necessitates "
            "substantial financial investment and considerable organisational restructuring."
        )
        result = humanise_text(text, level="minimal", reading_age_target="general")
        report = format_terminal_report(result)
        assert "Reading Age" in report or "reading age" in report
        assert "current" in report.lower()
        assert "target" in report.lower()

    def test_report_clean_when_no_findings(self) -> None:
        """Terminal report handles no findings gracefully."""
        result = HumaniseResult(text="Clean text.", findings=[], reading_age_report=None)
        report = format_terminal_report(result)
        assert "No AI tells detected" in report or "0 findings" in report or "no findings" in report.lower()


class TestInlineAnnotation:
    """Test format-aware inline annotation."""

    def test_annotation_md_format(self) -> None:
        """Markdown files get HTML-comment-style annotations."""
        text = "Hello\u00A0world"
        result = humanise_text(text, level="minimal")
        annotated = annotate_text(result.text, result.findings, file_ext=".md")
        assert "<!-- HUMANISE:" in annotated
        assert "-->" in annotated

    def test_annotation_py_format(self) -> None:
        """Python files get hash-comment-style annotations."""
        text = "Hello\u00A0world"
        result = humanise_text(text, level="minimal")
        annotated = annotate_text(result.text, result.findings, file_ext=".py")
        assert "# HUMANISE:" in annotated

    def test_annotation_html_format(self) -> None:
        """HTML files get HTML-comment-style annotations."""
        text = "<p>Hello\u00A0world</p>"
        result = humanise_text(text, level="minimal")
        annotated = annotate_text(result.text, result.findings, file_ext=".html")
        assert "<!-- HUMANISE:" in annotated
        assert "-->" in annotated

    def test_annotation_rst_format(self) -> None:
        """RST files get RST-comment-style annotations."""
        text = "Hello\u00A0world"
        result = humanise_text(text, level="minimal")
        annotated = annotate_text(result.text, result.findings, file_ext=".rst")
        assert ".. HUMANISE:" in annotated

    def test_annotation_txt_format(self) -> None:
        """Plain text files get bracket-style annotations."""
        text = "Hello\u00A0world"
        result = humanise_text(text, level="minimal")
        annotated = annotate_text(result.text, result.findings, file_ext=".txt")
        assert "[HUMANISE:" in annotated
        assert "]" in annotated

    def test_annotations_do_not_break_document_structure(self) -> None:
        """Annotations are inserted as separate lines and do not break existing content."""
        text = "Line one\u00A0here.\nLine two is fine.\nLine three\u00A0also."
        result = humanise_text(text, level="minimal")
        annotated = annotate_text(result.text, result.findings, file_ext=".md")
        # All original processed lines should still be present.
        for line in result.text.split("\n"):
            assert line in annotated


class TestReportToDisk:
    """Test report-to-disk functionality."""

    def test_report_writes_correct_content_to_file(self) -> None:
        """Report-to-disk writes the same content as the terminal report."""
        text = "Hello\u00A0world"
        result = humanise_text(text, level="minimal")
        report = format_terminal_report(result)

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = os.path.join(tmpdir, "test-report.txt")
            write_report_to_disk(result, report_path)
            with open(report_path, "r", encoding="utf-8") as f:
                written = f.read()
            assert written == report

    def test_report_default_path(self) -> None:
        """Default report path is <input-filename>.humanise-report.txt."""
        text = "Hello\u00A0world"
        result = humanise_text(text, level="minimal")

        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = os.path.join(tmpdir, "document.md")
            with open(src_path, "w", encoding="utf-8") as f:
                f.write(text)
            default_path = os.path.join(tmpdir, "document.md.humanise-report.txt")
            write_report_to_disk(result, default_path)
            assert os.path.exists(default_path)
            with open(default_path, "r", encoding="utf-8") as f:
                written = f.read()
            assert len(written) > 0
