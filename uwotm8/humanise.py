"""Humanise module for detecting and removing AI-generated text patterns.

This module provides the core processing engine for the ``--humanise``
feature. It applies character-level and structural AI tell replacements
to input text, recording each finding with line numbers and excerpts.
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Generator, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

from uwotm8.tells import TellCategory, TellTier, get_tells_for_tier

# Mapping from CLI level strings to TellTier enum values.
_LEVEL_TO_TIER: dict[str, TellTier] = {
    "minimal": TellTier.MINIMAL,
    "moderate": TellTier.MODERATE,
    "full": TellTier.FULL,
}

# Mapping from CLI rewrite sub-option names to tell registry names.
_REWRITE_OPTION_TO_TELL_NAME: dict[str, str] = {
    "filler-phrases": "filler_phrases",
    "hedging": "hedging_language",
    "bullet-lists": "bullet_list_after_single_sentence",
    "uniform-paragraphs": "uniform_paragraph_length",
    "repetitive-transitions": "repetitive_transitions",
}

# Default file extensions to process when walking directories.
_DEFAULT_EXTENSIONS: set[str] = {".md", ".txt", ".py", ".rst", ".html"}


@dataclass
class HumaniseResult:
    """Result of running humanise processing on a piece of text.

    Attributes:
        text: The processed text after tell replacements.
        findings: A list of dicts, each recording a detected tell with
            keys ``tell_name``, ``line_number``, ``original``, and
            ``replacement``.
        reading_age_report: Optional reading age analysis report. Populated
            when a ``reading_age_target`` is provided to ``humanise_text``.
    """

    text: str
    findings: list[dict[str, Any]] = field(default_factory=list)
    reading_age_report: Optional[dict[str, Any]] = None


def _line_number_for_position(text: str, pos: int) -> int:
    """Return the 1-based line number for a character position in *text*.

    Args:
        text: The full source text.
        pos: A character offset into *text*.

    Returns:
        The 1-based line number containing *pos*.
    """
    return text.count("\n", 0, pos) + 1


def _should_rewrite_structural(tell_name: str, rewrite: Optional[list[str]]) -> bool:
    """Determine whether a structural tell should be rewritten.

    Args:
        tell_name: The registry name of the structural tell.
        rewrite: The list of rewrite sub-options from the CLI, or None.

    Returns:
        True if the tell should be rewritten, False if flag-only.
    """
    if rewrite is None:
        return False
    if "all" in rewrite:
        return True
    for option, mapped_name in _REWRITE_OPTION_TO_TELL_NAME.items():
        if option in rewrite and mapped_name == tell_name:
            return True
    return False


def _capitalise_first(text: str) -> str:
    """Capitalise the first alphabetic character of *text*.

    Args:
        text: The input string.

    Returns:
        The string with its first letter upper-cased.
    """
    if not text:
        return text
    for i, ch in enumerate(text):
        if ch.isalpha():
            return text[:i] + ch.upper() + text[i + 1 :]
        # Skip leading whitespace or punctuation.
    return text


def _capitalise_after_punctuation(text: str) -> str:
    """Capitalise the first letter after sentence-ending punctuation.

    Finds patterns like ``". foo"`` or ``"! bar"`` and upper-cases the
    first alphabetic character following the punctuation + whitespace.

    Args:
        text: The input string.

    Returns:
        The string with post-punctuation letters capitalised.
    """

    def _upper(match: re.Match[str]) -> str:
        return match.group(1) + match.group(2).upper()

    return re.sub(r"([.!?]\s+)([a-z])", _upper, text)


def _rewrite_filler_or_hedging(text: str, pattern: re.Pattern[str]) -> str:
    """Remove filler/hedging phrases and clean up capitalisation.

    After removing the phrase the resulting text may start with a
    lower-case letter. This function ensures each resulting sentence
    begins with an upper-case letter.

    Args:
        text: The source text.
        pattern: Compiled regex matching the filler or hedging phrases.

    Returns:
        The cleaned text.
    """
    result = pattern.sub("", text)

    # Clean up: collapse multiple spaces, fix leading whitespace on lines,
    # and capitalise sentence starts.
    # Remove leading whitespace on each line that resulted from removal.
    result = re.sub(r"^[ \t]+", "", result, flags=re.MULTILINE)
    # Collapse multiple spaces into one.
    result = re.sub(r"  +", " ", result)
    # Capitalise after sentence-ending punctuation (e.g. ". foo" -> ". Foo").
    result = _capitalise_after_punctuation(result)
    # Capitalise the first letter of each line.
    lines = result.split("\n")
    cleaned_lines: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if stripped:
            leading = line[: len(line) - len(stripped)]
            cleaned_lines.append(leading + _capitalise_first(stripped))
        else:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def _rewrite_bullet_list(text: str, pattern: re.Pattern[str]) -> str:
    """Rewrite single-sentence-then-bullet-list patterns into flowing prose.

    Detects matches of the bullet-list pattern, extracts the intro
    sentence and bullet items, and merges them into a single sentence
    with a comma-separated list ending with "and".

    Args:
        text: The source text.
        pattern: Compiled regex matching bullet-list-after-single-sentence.

    Returns:
        The restructured text.
    """

    def _merge(match: re.Match[str]) -> str:
        block = match.group()
        lines = block.strip().split("\n")
        # First line is the introductory sentence.
        intro = lines[0].rstrip()
        # Remove trailing period/punctuation from intro for merging.
        if intro and intro[-1] in ".!?":
            intro_base = intro[:-1].rstrip()
            punctuation = intro[-1]
        else:
            intro_base = intro
            punctuation = "."

        # Extract bullet items.
        items: list[str] = []
        for line in lines[1:]:
            stripped = re.sub(r"^\s*[-*]\s+", "", line).strip()
            if stripped:
                # Lower-case the first letter for inline list.
                items.append(stripped[0].lower() + stripped[1:] if stripped else stripped)

        if not items:
            return block

        if len(items) == 1:
            merged = f"{intro_base}, including {items[0]}{punctuation}"
        elif len(items) == 2:
            merged = f"{intro_base}, including {items[0]} and {items[1]}{punctuation}"
        else:
            joined = ", ".join(items[:-1]) + ", and " + items[-1]
            merged = f"{intro_base}, including {joined}{punctuation}"

        return merged + "\n"

    return pattern.sub(_merge, text)


def _rewrite_repetitive_transitions(text: str, pattern: re.Pattern[str]) -> str:
    """Remove or vary repetitive transition words.

    When two or more of Furthermore/Moreover/Additionally appear in
    close proximity, remove all but the first occurrence (strip the
    transition word and its trailing comma/space, then capitalise the
    next word).

    Args:
        text: The source text.
        pattern: Compiled regex matching repetitive transitions.

    Returns:
        The text with subsequent transition words removed.
    """
    transition_re = re.compile(
        r"^(\s*)(Furthermore|Moreover|Additionally),?\s*",
        re.MULTILINE,
    )

    matches = list(transition_re.finditer(text))
    if len(matches) < 2:
        return text

    # Keep the first occurrence, remove subsequent ones.
    result = text
    # Process in reverse order to preserve positions.
    for m in reversed(matches[1:]):
        before = result[: m.start()]
        after = result[m.end() :]
        # Capitalise the first letter of the remaining text on this line.
        after = _capitalise_first(after)
        result = before + m.group(1) + after

    return result


def humanise_text(
    text: str,
    level: str = "moderate",
    rewrite: Optional[list[str]] = None,
    reading_age_target: Optional[Union[int, str]] = None,
) -> HumaniseResult:
    """Apply AI tell detection and replacements to *text*.

    Character-level tells that match the requested tier are always applied
    (the text is modified). Structural tells are recorded as findings but
    only rewritten when ``rewrite`` includes the relevant sub-option or
    ``"all"``.

    Args:
        text: The input text to process.
        level: Aggressiveness tier -- one of ``"minimal"``, ``"moderate"``,
            or ``"full"`` (default ``"moderate"``).
        rewrite: Optional list of structural rewrite sub-options, or
            ``["all"]`` to rewrite all structural tells. When ``None``,
            structural tells are flagged only.
        reading_age_target: Optional target reading age as an integer or
            descriptive level string (e.g. ``"general"``). When provided,
            a reading age analysis is included in the result.

    Returns:
        A ``HumaniseResult`` containing the processed text, a list of
        findings, and an optional reading age report.
    """
    tier = _LEVEL_TO_TIER.get(level, TellTier.MODERATE)
    tells = get_tells_for_tier(tier)

    character_tells = [t for t in tells if t.category is TellCategory.CHARACTER]
    structural_tells = [t for t in tells if t.category is TellCategory.STRUCTURAL]

    findings: list[dict[str, Any]] = []
    result_text = text

    # --- Character-level tells (always applied) ---
    for tell in character_tells:
        pattern = tell.pattern
        if not isinstance(pattern, re.Pattern):
            continue

        replacement = tell.replacement
        if replacement is None:
            for match in pattern.finditer(result_text):
                findings.append(
                    {
                        "tell_name": tell.name,
                        "line_number": _line_number_for_position(result_text, match.start()),
                        "original": match.group(),
                        "replacement": None,
                    }
                )
            continue

        matches = list(pattern.finditer(result_text))
        for match in matches:
            if callable(replacement):
                replacement_text = replacement(match)
            else:
                replacement_text = match.expand(replacement)
            findings.append(
                {
                    "tell_name": tell.name,
                    "line_number": _line_number_for_position(result_text, match.start()),
                    "original": match.group(),
                    "replacement": replacement_text,
                }
            )

        if callable(replacement):
            result_text = pattern.sub(replacement, result_text)
        else:
            result_text = pattern.sub(replacement, result_text)

    # --- Structural tells (flag by default, rewrite when opted in) ---
    for tell in structural_tells:
        pattern = tell.pattern
        if not isinstance(pattern, re.Pattern):
            continue

        matches = list(pattern.finditer(result_text))
        if not matches:
            continue

        should_rewrite = _should_rewrite_structural(tell.name, rewrite)

        # Record findings for all matches.
        for match in matches:
            findings.append(
                {
                    "tell_name": tell.name,
                    "line_number": _line_number_for_position(result_text, match.start()),
                    "original": match.group(),
                    "replacement": None if not should_rewrite else "(rewritten)",
                }
            )

        if not should_rewrite:
            continue

        # Apply the appropriate rewrite strategy.
        if tell.name == "filler_phrases":
            result_text = _rewrite_filler_or_hedging(result_text, pattern)
        elif tell.name == "hedging_language":
            result_text = _rewrite_filler_or_hedging(result_text, pattern)
        elif tell.name == "bullet_list_after_single_sentence":
            result_text = _rewrite_bullet_list(result_text, pattern)
        elif tell.name == "repetitive_transitions":
            result_text = _rewrite_repetitive_transitions(result_text, pattern)
        elif tell.name == "uniform_paragraph_length":
            # Uniform paragraphs are flag-only even in rewrite mode;
            # there is no automatic rewrite -- just the suggestion to
            # vary paragraph length.
            pass

    # --- Reading age analysis (when target is provided) ---
    reading_age_report: Optional[dict[str, Any]] = None
    if reading_age_target is not None:
        from uwotm8.readability import analyse_reading_age

        reading_age_report = analyse_reading_age(result_text, reading_age_target)

    return HumaniseResult(
        text=result_text,
        findings=findings,
        reading_age_report=reading_age_report,
    )


# ---------------------------------------------------------------------------
# File processing
# ---------------------------------------------------------------------------


def _extract_python_comments_and_docstrings(content: str) -> list[tuple[int, int, str]]:
    """Extract comment and docstring regions from Python source code.

    Returns a list of (start, end, text) tuples representing regions
    that contain comments or docstrings.

    Args:
        content: The full Python source code.

    Returns:
        A list of (start_offset, end_offset, region_text) tuples.
    """
    regions: list[tuple[int, int, str]] = []

    # Single-line comments.
    for match in re.finditer(r"#[^\n]*", content):
        regions.append((match.start(), match.end(), match.group()))

    # Triple-quoted strings (docstrings).
    for match in re.finditer(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', content):
        regions.append((match.start(), match.end(), match.group()))

    return sorted(regions, key=lambda r: r[0])


def _humanise_docx_file(
    src_path: Path,
    dst: Optional[Union[str, Path]],
    level: str,
    rewrite: Optional[list[str]],
    reading_age_target: Optional[Union[int, str]],
    check: bool,
    strict: bool,
    annotate: bool,
) -> HumaniseResult:
    """Apply humanisation to a DOCX file, preserving run-level formatting.

    Reads text from each paragraph's runs, applies tells to the text of
    each run individually, then writes the modified text back to the
    runs so that bold, italic, font, and other formatting is preserved.

    Args:
        src_path: Source ``.docx`` file path.
        dst: Destination file path. If ``None``, writes back to *src_path*.
        level: Aggressiveness tier.
        rewrite: Structural rewrite sub-options.
        reading_age_target: Optional reading age target.
        check: If ``True``, do not modify the file.
        strict: If ``True``, raise exceptions on processing errors.
        annotate: If ``True``, inline annotations are noted in findings
            but not inserted into the DOCX structure.

    Returns:
        A ``HumaniseResult`` for the file.

    Raises:
        ImportError: If ``python-docx`` is not installed.
    """
    if not _has_docx_support():
        raise ImportError(
            "python-docx is required to process .docx files. "
            "Install it with: pip install uwotm8[docx]"
        )

    import docx

    document = docx.Document(str(src_path))

    # Collect all text for a combined result (for reading age, etc.).
    all_findings: list[dict[str, Any]] = []
    all_text_parts: list[str] = []
    changed = False

    # Track a running line number across paragraphs.
    current_line = 1

    for paragraph in document.paragraphs:
        para_text = paragraph.text
        all_text_parts.append(para_text)

        # Process each run individually to preserve formatting.
        for run in paragraph.runs:
            original_run_text = run.text
            if not original_run_text:
                continue

            result = humanise_text(
                original_run_text,
                level=level,
                rewrite=rewrite,
                reading_age_target=None,  # Reading age on full text only.
            )

            # Adjust line numbers relative to document position.
            for finding in result.findings:
                adjusted = dict(finding)
                adjusted["line_number"] = finding["line_number"] + current_line - 1
                all_findings.append(adjusted)

            if result.text != original_run_text:
                run.text = result.text
                changed = True

        # Each paragraph roughly corresponds to a line.
        current_line += para_text.count("\n") + 1

    # Build the combined text for the result and reading age.
    combined_text = "\n".join(all_text_parts)

    # Reading age analysis on the full combined text.
    reading_age_report: Optional[dict[str, Any]] = None
    if reading_age_target is not None:
        from uwotm8.readability import analyse_reading_age

        reading_age_report = analyse_reading_age(combined_text, reading_age_target)

    if not check and changed:
        dst_path = Path(dst) if dst is not None else src_path
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        document.save(str(dst_path))

    return HumaniseResult(
        text=combined_text,
        findings=all_findings,
        reading_age_report=reading_age_report,
    )


def humanise_file(
    src: Union[str, Path],
    dst: Optional[Union[str, Path]] = None,
    level: str = "moderate",
    rewrite: Optional[list[str]] = None,
    reading_age_target: Optional[Union[int, str]] = None,
    check: bool = False,
    strict: bool = False,
    annotate: bool = False,
    comments_only: bool = False,
) -> HumaniseResult:
    """Apply humanisation to a file.

    Follows the same read-process-compare-write pattern as
    ``convert_file()`` in ``convert.py``.

    Args:
        src: Source file path.
        dst: Destination file path. If ``None``, writes back to *src*.
        level: Aggressiveness tier.
        rewrite: Structural rewrite sub-options.
        reading_age_target: Optional reading age target.
        check: If ``True``, do not modify the file.
        strict: If ``True``, raise exceptions on processing errors.
        annotate: If ``True``, insert inline annotations.
        comments_only: If ``True`` and the file is ``.py``, only
            process comments and docstrings.

    Returns:
        A ``HumaniseResult`` for the file.
    """
    src_path = Path(src)
    if not src_path.exists():
        raise FileNotFoundError(f"File not found: {src_path}")

    file_ext = src_path.suffix.lower()

    # Dispatch to DOCX-specific handler for .docx files.
    if file_ext == ".docx":
        return _humanise_docx_file(
            src_path=src_path,
            dst=dst,
            level=level,
            rewrite=rewrite,
            reading_age_target=reading_age_target,
            check=check,
            strict=strict,
            annotate=annotate,
        )

    with open(src_path, encoding="utf-8") as f:
        content = f.read()

    if comments_only and file_ext == ".py":
        result = _humanise_python_comments_only(
            content,
            level=level,
            rewrite=rewrite,
            reading_age_target=reading_age_target,
        )
    else:
        result = humanise_text(
            content,
            level=level,
            rewrite=rewrite,
            reading_age_target=reading_age_target,
        )

    output_text = result.text

    # Insert inline annotations if requested.
    if annotate and result.findings:
        from uwotm8.output import annotate_text

        output_text = annotate_text(output_text, result.findings, file_ext)

    # Determine whether changes were made.
    changed = output_text != content

    if check:
        # In check mode, do not write changes.
        return result

    if changed:
        dst_path = Path(dst) if dst is not None else src_path
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dst_path, "w", encoding="utf-8") as f:
            f.write(output_text)

    return result


def _humanise_python_comments_only(
    content: str,
    level: str = "moderate",
    rewrite: Optional[list[str]] = None,
    reading_age_target: Optional[Union[int, str]] = None,
) -> HumaniseResult:
    """Apply humanisation only to comments and docstrings in Python source.

    Code outside comments and docstrings is left untouched.

    Args:
        content: The full Python source code.
        level: Aggressiveness tier.
        rewrite: Structural rewrite sub-options.
        reading_age_target: Optional reading age target.

    Returns:
        A ``HumaniseResult`` with the processed content.
    """
    regions = _extract_python_comments_and_docstrings(content)
    all_findings: list[dict[str, Any]] = []
    result_content = content

    # Process regions in reverse order to preserve offsets.
    for start, end, region_text in reversed(regions):
        region_result = humanise_text(
            region_text,
            level=level,
            rewrite=rewrite,
            reading_age_target=None,  # Reading age on full text only.
        )
        if region_result.text != region_text:
            result_content = result_content[:start] + region_result.text + result_content[end:]

        # Adjust line numbers for findings relative to the region position.
        line_offset = content.count("\n", 0, start)
        for finding in region_result.findings:
            adjusted = dict(finding)
            adjusted["line_number"] = finding["line_number"] + line_offset
            all_findings.append(adjusted)

    # Re-sort findings by line number.
    all_findings.sort(key=lambda f: f.get("line_number", 0))

    # Reading age on the full text if requested.
    reading_age_report: Optional[dict[str, Any]] = None
    if reading_age_target is not None:
        from uwotm8.readability import analyse_reading_age

        reading_age_report = analyse_reading_age(result_content, reading_age_target)

    return HumaniseResult(
        text=result_content,
        findings=all_findings,
        reading_age_report=reading_age_report,
    )


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------


def humanise_stream(
    stream: Iterable[str],
    level: str = "moderate",
    rewrite: Optional[list[str]] = None,
    reading_age_target: Optional[Union[int, str]] = None,
) -> Generator[str, None, None]:
    """Apply humanisation to a stream of lines.

    Buffers all input to handle structural tells that need multi-line
    context, then yields processed lines. The terminal report is written
    to stderr.

    Args:
        stream: An iterable of strings (e.g. ``sys.stdin``).
        level: Aggressiveness tier.
        rewrite: Structural rewrite sub-options.
        reading_age_target: Optional reading age target.

    Yields:
        Processed lines of text.
    """
    # Buffer all input for multi-line structural tell detection.
    full_text = "".join(stream)

    result = humanise_text(
        full_text,
        level=level,
        rewrite=rewrite,
        reading_age_target=reading_age_target,
    )

    # Write the terminal report to stderr.
    if result.findings or result.reading_age_report:
        from uwotm8.output import format_terminal_report

        report = format_terminal_report(result)
        sys.stderr.write(report)

    # Yield the processed text line by line.
    for line in result.text.splitlines(True):
        yield line


# ---------------------------------------------------------------------------
# Directory / path processing
# ---------------------------------------------------------------------------


def _has_docx_support() -> bool:
    """Check whether the optional ``python-docx`` dependency is available.

    Returns:
        ``True`` if ``python-docx`` can be imported.
    """
    try:
        import docx  # noqa: F401

        return True
    except ImportError:
        return False


def humanise_paths(
    paths: list[Union[str, Path]],
    level: str = "moderate",
    rewrite: Optional[list[str]] = None,
    reading_age_target: Optional[Union[int, str]] = None,
    check: bool = False,
    strict: bool = False,
    annotate: bool = False,
    comments_only: bool = False,
    report_path: Optional[str] = None,
) -> tuple[int, int, list[HumaniseResult]]:
    """Process multiple files and directories for humanisation.

    Follows the same directory-walking pattern as ``process_paths()``
    in ``convert.py``. Adds ``.rst`` and ``.html`` to the default
    include extensions, and ``.docx`` when the optional dependency is
    available.

    Args:
        paths: List of file and directory paths.
        level: Aggressiveness tier.
        rewrite: Structural rewrite sub-options.
        reading_age_target: Optional reading age target.
        check: If ``True``, do not modify files.
        strict: If ``True``, raise on processing errors.
        annotate: If ``True``, insert inline annotations.
        comments_only: If ``True``, only process comments in ``.py`` files.
        report_path: Optional path for saving the report to disk.

    Returns:
        A tuple of (total_files, modified_files, list_of_results).
    """
    extensions = set(_DEFAULT_EXTENSIONS)
    if _has_docx_support():
        extensions.add(".docx")

    total_count = 0
    modified_count = 0
    all_results: list[HumaniseResult] = []

    file_list: list[Path] = []
    for path_str in paths:
        path = Path(path_str)
        if path.is_file():
            file_list.append(path)
        elif path.is_dir():
            for root, _, files in os.walk(path):
                for fname in files:
                    file_path = Path(root) / fname
                    if file_path.suffix.lower() in extensions:
                        file_list.append(file_path)

    for file_path in file_list:
        total_count += 1
        try:
            result = humanise_file(
                src=file_path,
                level=level,
                rewrite=rewrite,
                reading_age_target=reading_age_target,
                check=check,
                strict=strict,
                annotate=annotate,
                comments_only=comments_only,
            )
            all_results.append(result)
            if result.findings:
                modified_count += 1
        except Exception:
            if strict:
                raise
            # Skip files that cause errors in non-strict mode.

    return total_count, modified_count, all_results
