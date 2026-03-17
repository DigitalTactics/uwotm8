# Specification: AI Tell Removal (--humanise)

## Goal
Extend the uwotm8 CLI with a `--humanise` flag that detects and removes common AI-generated text patterns ("tells") from documents, making text feel more naturally human-written for a European business audience.

## User Stories
- As a content editor, I want to run `uwotm8 --humanise report.md` so that AI-generated tells are flagged in a terminal report without modifying my file.
- As a technical writer, I want to run `uwotm8 --humanise --rewrite all --level moderate docs/` so that character-level and structural AI tells are automatically rewritten across my documentation.
- As a communications lead, I want to see a reading age analysis with simplification suggestions so that I can ensure content is accessible to a general UK audience.

## Specific Requirements

**New CLI flags on the existing `uwotm8` command**
- `--humanise` activates AI tell detection. Without it, no humanisation logic runs. Independent of spelling conversion; both can be combined explicitly but neither implies the other.
- `--rewrite` accepts `all` or a comma-separated list of sub-options: `bullet-lists`, `filler-phrases`, `hedging`, `uniform-paragraphs`, `repetitive-transitions`. Requires `--humanise`. When absent, `--humanise` defaults to flagging-only (no file modifications for structural tells; character-level tells are always applied).
- `--annotate` adds inline comments directly in the file marking each flagged tell. Format-aware: HTML comments for `.html`, markdown comments or inline markers for `.md`, Python `#` comments for `.py`, RST comments for `.rst`, plain-text brackets for `.txt`.
- `--level` accepts `minimal`, `moderate`, or `full` (default `moderate`). Controls aggressiveness of detection and rewriting.
- `--reading-age` accepts either a numeric age (e.g. `14`) or a descriptive level (`basic`, `general`, `advanced`, `technical`). Triggers reading age analysis and simplification suggestions in the report.
- `--report` accepts an optional file path. Saves the terminal report to disk. If no path given, writes to `<input-filename>.humanise-report.txt` alongside the source.

**New module: `uwotm8/humanise.py`**
- All humanisation logic lives in this module, completely separate from `convert.py`.
- Exposes a public API: `humanise_text(text, level, rewrite, reading_age_target)` for programmatic use, plus `humanise_file()` and `humanise_stream()` following the same patterns as `convert.py`.
- The `main()` function in `convert.py` is extended to parse the new flags and dispatch to `humanise.py` functions when `--humanise` is present.

**AI tells registry (class-based pattern)**
- Create `uwotm8/tells.py` containing a registry of AI tell definitions using a class-based pattern with dataclasses.
- Each tell is a dataclass instance with fields: `name` (str), `category` (enum: `character` or `structural`), `pattern` (compiled regex or callable), `replacement` (str, callable, or None for flagging-only), `description` (str), `tier` (enum: `minimal`, `moderate`, or `full`).
- The registry is a list of tell instances. Adding a new tell means appending a new dataclass instance -- no other code changes required.
- Character-level tells include: em dash to comma/restructured clause, non-breaking spaces to normal spaces, smart quotes to straight quotes, Unicode ellipsis to three periods, excessive bold/italic markdown stripping, zero-width characters removal, en dash normalisation, fancy Unicode bullets to plain hyphens.
- Structural tells include: filler phrase detection (e.g. "It's important to note that", "In today's world", "Let's dive in"), hedging language detection (e.g. "It's worth noting", "arguably", "one might say"), bullet-list-after-single-sentence pattern, uniform paragraph length detection, repetitive transition words (e.g. "Furthermore", "Moreover", "Additionally" appearing in sequence).

**Tiered aggressiveness levels**
- `minimal`: character-level normalisation only (non-breaking spaces, zero-width chars, smart quotes, Unicode normalisation). Safe for all content types including scientific text.
- `moderate` (default): everything in minimal plus em dash replacement, excessive markdown formatting reduction, filler phrase detection, and hedging language detection.
- `full`: everything in moderate plus structural pattern detection (bullet list restructuring, uniform paragraph flagging, repetitive transition detection).

**Reading age analysis**
- Implement in a separate submodule or section within `humanise.py`.
- Calculate using a combination of Flesch-Kincaid Grade Level, Gunning Fog Index, and Coleman-Liau Index. Average the results for a composite score.
- Map composite scores to descriptive levels: `basic` (age 9-11), `general` (age 12-14), `advanced` (age 15-17), `technical` (age 18+).
- When `--reading-age` is specified, the report includes: current reading age (numeric and descriptive), target reading age, delta, and per-paragraph suggestions for sentences that exceed the target (e.g. "Sentence on line 42 has a Flesch-Kincaid grade of 16; consider splitting or simplifying").
- Readability formulae must handle UK English text correctly (the tool already converts to British spelling, so input may contain British spellings).

**Output modes**
- Terminal report (default when `--humanise` is used): prints a summary of detected tells grouped by category, with line numbers and excerpts. Includes counts per tell type, a severity summary, and reading age analysis if `--reading-age` is set.
- Inline annotation (`--annotate`): inserts format-aware comments in the source file at each detected tell location. Must not break document structure or syntax.
- Save to disk (`--report <path>`): writes the same content as the terminal report to a file. Compatible with `--annotate` (both can be used together).

**File format support**
- `.md`, `.txt`, `.py`, `.rst`, `.html`: supported out of the box. Each format has format-aware annotation insertion logic.
- `.docx`: supported via optional dependency. Install with `pip install uwotm8[docx]`. When `.docx` files are encountered without the dependency, print a clear error message suggesting the install command. Use `python-docx` for reading/writing. Extract text from paragraphs and runs, apply tells, write back preserving formatting.
- stdin/stdout: supported, following the same pattern as `convert_stream()`. Terminal report goes to stderr when processing stdin.
- The existing `--include` flag default must be extended to include `.rst` and `.html` when `--humanise` is active. `.docx` is included only when the optional dependency is available.

**Integration with existing flags**
- `--humanise` + `--check`: dry-run mode. Reports what tells would be found/rewritten but makes no file changes. Returns exit code 1 if tells are detected, 0 if clean.
- `--humanise` + `--strict`: raises exceptions on processing errors instead of silently skipping.
- `--humanise` + `--comments-only`: for `.py` files, only analyses comments and docstrings for AI tells.
- `--humanise` combined with no other flags (no `--strict`, no spelling conversion): runs humanisation only, no spelling conversion.
- `uwotm8 --humanise --strict src/`: runs both humanisation and strict spelling conversion.

**Dependencies**
- `textstat` (or equivalent) for readability index calculations -- add as a required dependency if using an external library, or implement the three formulae directly (Flesch-Kincaid, Gunning Fog, Coleman-Liau) to avoid a new dependency. The spec recommends implementing directly to keep the dependency footprint small.
- `python-docx` as an optional dependency under the `docx` extras group in `pyproject.toml`.

## Existing Code to Leverage

**CLI argument parsing in `convert.py:main()` (lines 457-562)**
- Uses `argparse.ArgumentParser` with positional `src` args and optional flags (`--check`, `--strict`, `--comments-only`, `--include`, `--exclude`, `--output`, `--ignore`).
- New `--humanise`, `--rewrite`, `--annotate`, `--level`, `--reading-age`, and `--report` flags should be added to this same parser.
- The dispatch logic after `args = parser.parse_args()` should be extended to call `humanise.py` functions when `--humanise` is present.

**File processing pipeline (`process_paths`, `_process_file`, `convert_file`)**
- `process_paths()` (line 390) walks directories, filters by extension, and delegates to `_process_file()`. This pattern should be replicated in `humanise.py` with a `humanise_paths()` function.
- `convert_file()` (line 145) reads a file, processes content, compares for changes, and writes back. The same read-process-compare-write pattern should be followed by `humanise_file()`.
- `_handle_file_with_output()` (line 430) handles the `-o` output flag for single files. A similar handler is needed for humanise output.

**Streaming pattern (`convert_stream`, lines 130-142)**
- Generator-based line-by-line processing for stdin/stdout. `humanise_stream()` should follow the same generator pattern but note that some structural tells require multi-line context, so buffering may be needed.

**`CONVERSION_IGNORE_LIST` dictionary pattern (lines 13-30)**
- A module-level dictionary used for extensible word exclusions. The AI tells registry should use a more structured class-based pattern (dataclasses) but the principle of a module-level, easily-editable registry is the same.

**Check mode and exit code pattern (lines 548-562)**
- When `--check` is set, no files are written and the exit code signals whether changes would be made. The humanise check mode should follow the same convention: exit 0 for clean, exit 1 for tells detected.

## Out of Scope
- Non-English text detection or processing
- Real-time / watch mode for file changes
- Creating a separate subcommand (using `--humanise` flag on existing command)
- Automatic spelling conversion when `--humanise` is used (must be combined explicitly)
- Machine-learning-based or LLM-based tell detection (this feature uses deterministic regex and heuristic patterns only)
- Semantic rewriting of content (structural `--rewrite` restructures patterns but does not rephrase sentences for meaning)
- GUI or web interface
- Integration with external AI detection services or APIs
- Conversion of document layouts or embedded images in `.docx` files
- Support for `.pdf`, `.odt`, or other document formats beyond those listed
