# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

uwotm8 is a Python tool that converts American English spelling to British English spelling in text and code files. It uses the `breame` library for spelling dictionary lookups.

## Common Commands

```bash
# Install dependencies (creates venv, installs poetry, pre-commit hooks)
make install

# Run all quality checks (poetry check, pre-commit, mypy, deptry)
make check

# Run tests with coverage
make test

# Format code with ruff
make format

# Build documentation and serve locally
make docs

# Multi-version testing (Python 3.8, 3.9, 3.10, 3.11)
tox
```

### Running a Single Test

```bash
pytest tests/test_convert.py::TestConvertAmericanToBritishSpelling::test_name -v
```

## Architecture

### Core Module: `uwotm8/convert.py`

The entire conversion logic lives in a single module with these key functions:

- **`convert_american_to_british_spelling(text, strict=False)`** - Core conversion engine using regex pattern matching
- **`convert_stream(stream, strict=False)`** - Generator-based streaming for stdin/stdout
- **`convert_file(src, dst, strict, check)`** - File-based conversion
- **`convert_python_comments_only(src, dst, strict, check)`** - Converts only Python comments and docstrings, preserving code
- **`process_paths(paths, check, strict, comments_only)`** - Batch processing of files/directories
- **`main()`** - CLI entry point

### Key Data Structure

**`CONVERSION_IGNORE_LIST`** (lines 13-30) - Dictionary of American spellings to skip (e.g., "program", "disk", "analog" - terms commonly used in technical contexts)

### Context-Aware Conversion

The converter intelligently skips:
- Words in code blocks (backtick-delimited)
- Words on lines containing URLs (http://, https://, www.)
- Hyphenated terms
- Words in the ignore list

### Entry Points

1. **CLI:** `uwotm8` command (defined in pyproject.toml)
2. **Python API:** `from uwotm8 import convert_american_to_british_spelling`
3. **Module:** `python -m uwotm8`

## Code Quality Requirements

- **Type hints:** Required on all functions (mypy with `disallow_untyped_defs = True`)
- **Line length:** 120 characters max
- **Docstrings:** Google-style format
- **Tests:** pytest with branch coverage; add tests before implementing features
