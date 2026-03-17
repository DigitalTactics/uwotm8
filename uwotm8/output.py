"""Output modes for the humanise feature.

This module provides three output modes:

1. **Terminal report** -- a human-readable summary of detected AI tells,
   grouped by category, with line numbers, excerpts, counts, and an
   optional reading age section.
2. **Inline annotation** -- format-aware comments inserted into the
   source text at each finding's line position.
3. **Report-to-disk** -- writes the terminal report content to a file.
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Any, Optional

from uwotm8.humanise import HumaniseResult
from uwotm8.tells import TELLS, TellCategory


# ---------------------------------------------------------------------------
# Category label helpers
# ---------------------------------------------------------------------------

def _category_for_tell_name(tell_name: str) -> str:
    """Return a human-readable category label for a tell name.

    Args:
        tell_name: The machine-friendly tell name from the registry.

    Returns:
        ``"Character-level"`` or ``"Structural"``, falling back to
        ``"Other"`` if the tell is not in the registry.
    """
    for tell in TELLS:
        if tell.name == tell_name:
            if tell.category is TellCategory.CHARACTER:
                return "Character-level"
            return "Structural"
    return "Other"


# ---------------------------------------------------------------------------
# Terminal report formatter
# ---------------------------------------------------------------------------

def format_terminal_report(result: HumaniseResult) -> str:
    """Format a ``HumaniseResult`` as a human-readable terminal report.

    The report groups findings by category (character-level, structural),
    shows line numbers and excerpts for each finding, and includes counts
    per tell type with a severity summary. When a reading age report is
    present it is appended as a separate section.

    Args:
        result: The result from ``humanise_text()``.

    Returns:
        A multi-line string suitable for printing to a terminal or
        writing to a file.
    """
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("Humanise Report")
    lines.append("=" * 60)
    lines.append("")

    if not result.findings:
        lines.append("No AI tells detected.")
        lines.append("")
    else:
        # Group findings by category.
        by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for finding in result.findings:
            cat = _category_for_tell_name(finding["tell_name"])
            by_category[cat].append(finding)

        # Print each category.
        for category in ("Character-level", "Structural", "Other"):
            findings_in_cat = by_category.get(category)
            if not findings_in_cat:
                continue
            lines.append(f"--- {category} tells ---")
            lines.append("")
            for finding in findings_in_cat:
                line_num = finding.get("line_number", "?")
                tell_name = finding.get("tell_name", "unknown")
                original = finding.get("original", "")
                replacement = finding.get("replacement")
                # Truncate long excerpts.
                excerpt = repr(original)
                if len(excerpt) > 80:
                    excerpt = excerpt[:77] + "..."
                entry = f"  Line {line_num}: {tell_name} -- {excerpt}"
                if replacement is not None:
                    repl_repr = repr(replacement)
                    if len(repl_repr) > 40:
                        repl_repr = repl_repr[:37] + "..."
                    entry += f" -> {repl_repr}"
                lines.append(entry)
            lines.append("")

        # Counts per tell type.
        lines.append("--- Summary ---")
        lines.append("")
        count_by_name: dict[str, int] = defaultdict(int)
        for finding in result.findings:
            count_by_name[finding["tell_name"]] += 1
        for name, count in sorted(count_by_name.items()):
            lines.append(f"  {name}: {count}")
        total = len(result.findings)
        lines.append("")
        lines.append(f"  Total findings: {total}")
        lines.append("")

    # Reading age section.
    if result.reading_age_report is not None:
        ra = result.reading_age_report
        lines.append("--- Reading Age Analysis ---")
        lines.append("")
        lines.append(f"  Current reading age: {ra.get('current_age', '?')} ({ra.get('current_level', '?')})")
        lines.append(f"  Target reading age:  {ra.get('target_age', '?')} ({ra.get('target_level', '?')})")
        lines.append(f"  Delta:               {ra.get('delta', '?')}")
        lines.append("")
        suggestions = ra.get("suggestions", [])
        if suggestions:
            lines.append("  Suggestions:")
            for suggestion in suggestions:
                lines.append(f"    - {suggestion}")
            lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Inline annotation
# ---------------------------------------------------------------------------

# Annotation format templates keyed by file extension.
_ANNOTATION_FORMATS: dict[str, tuple[str, str]] = {
    ".md": ("<!-- HUMANISE: ", " -->"),
    ".html": ("<!-- HUMANISE: ", " -->"),
    ".htm": ("<!-- HUMANISE: ", " -->"),
    ".py": ("# HUMANISE: ", ""),
    ".rst": (".. HUMANISE: ", ""),
    ".txt": ("[HUMANISE: ", "]"),
}


def _annotation_comment(description: str, file_ext: str) -> str:
    """Build a single annotation comment string.

    Args:
        description: The human-readable tell description.
        file_ext: The file extension (e.g. ``".md"``).

    Returns:
        A formatted annotation string.
    """
    prefix, suffix = _ANNOTATION_FORMATS.get(file_ext, ("[HUMANISE: ", "]"))
    return f"{prefix}{description}{suffix}"


def annotate_text(
    text: str,
    findings: list[dict[str, Any]],
    file_ext: str = ".txt",
) -> str:
    """Insert format-aware inline annotations into *text*.

    Annotations are inserted as new lines immediately *before* the line
    containing each finding so that the original document content is
    preserved intact.

    Args:
        text: The processed text (after tell replacements).
        findings: The list of finding dicts from ``HumaniseResult``.
        file_ext: The file extension used to choose annotation format.

    Returns:
        The annotated text with inline comments inserted.
    """
    if not findings:
        return text

    # Collect annotations grouped by line number.
    annotations_by_line: dict[int, list[str]] = defaultdict(list)
    for finding in findings:
        line_num = finding.get("line_number", 0)
        tell_name = finding.get("tell_name", "unknown")
        # Build a concise description from the tell registry.
        description = tell_name.replace("_", " ")
        for tell in TELLS:
            if tell.name == tell_name:
                description = tell.description
                break
        comment = _annotation_comment(description, file_ext)
        annotations_by_line[line_num].append(comment)

    # Rebuild text with annotations inserted before each affected line.
    source_lines = text.split("\n")
    output_lines: list[str] = []
    for idx, line in enumerate(source_lines, start=1):
        if idx in annotations_by_line:
            for comment in annotations_by_line[idx]:
                output_lines.append(comment)
        output_lines.append(line)

    return "\n".join(output_lines)


# ---------------------------------------------------------------------------
# Report to disk
# ---------------------------------------------------------------------------


def default_report_path(src_path: str) -> str:
    """Compute the default report file path for a given source file.

    The default is ``<src_path>.humanise-report.txt``.

    Args:
        src_path: The path to the source file being analysed.

    Returns:
        The default report file path.
    """
    return f"{src_path}.humanise-report.txt"


def write_report_to_disk(
    result: HumaniseResult,
    report_path: str,
) -> None:
    """Write the terminal report to a file on disk.

    Args:
        result: The ``HumaniseResult`` to format and write.
        report_path: The destination file path.
    """
    report_content = format_terminal_report(result)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
