# Task Breakdown: AI Tell Removal (--humanise)

## Overview
Total Tasks: 8 task groups, approximately 55 sub-tasks

This feature adds a `--humanise` flag to the existing `uwotm8` CLI that detects and removes common AI-generated text patterns ("tells") from documents. The implementation spans a tells registry, character-level and structural tell processors, reading age analysis, multiple output modes, CLI integration, and docx format support.

## Task List

### Foundation

#### Task Group 1: Tells Registry and Data Model
**Dependencies:** None

- [x] 1.0 Complete tells registry module
  - [x] 1.1 Write 4-6 focused tests for the tells registry
    - Test that a Tell dataclass can be instantiated with all required fields
    - Test that the registry list contains tells and can be filtered by category (character vs structural)
    - Test that tells can be filtered by tier (minimal, moderate, full)
    - Test that a tell pattern (regex) matches expected input
    - Test that adding a new tell to the registry requires no code changes beyond appending
  - [x] 1.2 Create `uwotm8/tells.py` with Tell dataclass and enums
    - Define `TellCategory` enum: `character`, `structural`
    - Define `TellTier` enum: `minimal`, `moderate`, `full`
    - Define `Tell` dataclass with fields: `name` (str), `category` (TellCategory), `pattern` (compiled regex or callable), `replacement` (str, callable, or None), `description` (str), `tier` (TellTier)
    - Follow Google-style docstrings and type hints per mypy requirements
  - [x] 1.3 Populate character-level tells in the registry
    - Non-breaking spaces to normal spaces (minimal tier)
    - Zero-width characters removal (minimal tier)
    - Smart quotes to straight quotes (minimal tier)
    - Unicode ellipsis to three periods (minimal tier)
    - Em dash to comma/restructured clause (moderate tier)
    - En dash normalisation (moderate tier)
    - Excessive bold/italic markdown stripping (moderate tier)
    - Fancy Unicode bullets to plain hyphens (moderate tier)
  - [x] 1.4 Populate structural tells in the registry
    - Filler phrase detection: "It's important to note that", "In today's world", "Let's dive in", etc. (moderate tier)
    - Hedging language detection: "It's worth noting", "arguably", "one might say", etc. (moderate tier)
    - Bullet-list-after-single-sentence pattern (full tier)
    - Uniform paragraph length detection (full tier)
    - Repetitive transition words: "Furthermore", "Moreover", "Additionally" in sequence (full tier)
  - [x] 1.5 Add helper function `get_tells_for_tier(tier: TellTier) -> list[Tell]` that returns all tells at or below the given tier
  - [x] 1.6 Ensure tells registry tests pass
    - Run ONLY the tests written in 1.1
    - Verify all tells are correctly categorised and tiered

**Acceptance Criteria:**
- Tell dataclass and enums are defined with full type hints
- Registry contains all specified character-level and structural tells
- Filtering by tier returns correct cumulative sets (minimal subset of moderate subset of full)
- Adding a new tell requires only appending a dataclass instance to the registry list
- Tests from 1.1 pass

---

### Core Processing Engine

#### Task Group 2: Character-Level Tell Processing
**Dependencies:** Task Group 1

- [x] 2.0 Complete character-level tell processing
  - [x] 2.1 Write 6-8 focused tests for character-level tell application
    - Test non-breaking space replacement
    - Test smart quote normalisation (single and double)
    - Test em dash replacement with comma
    - Test zero-width character removal
    - Test Unicode ellipsis replacement
    - Test excessive markdown bold/italic stripping
    - Test that tier filtering works (minimal tier skips em dash replacement)
    - Test that original text is unchanged when no tells are present
  - [x] 2.2 Create `uwotm8/humanise.py` with `humanise_text()` function
    - Signature: `humanise_text(text: str, level: str = "moderate", rewrite: Optional[list[str]] = None, reading_age_target: Optional[Union[int, str]] = None) -> HumaniseResult`
    - Define `HumaniseResult` dataclass to hold: `text` (str), `findings` (list of detected tells with line numbers and excerpts), `reading_age_report` (optional)
    - Apply character-level tells based on tier, always modifying text (character-level tells are always applied per spec)
  - [x] 2.3 Implement character-level tell application logic
    - Iterate through character-level tells from registry filtered by tier
    - Apply regex substitutions or callable replacements
    - Record each finding with: tell name, line number, original excerpt, replacement excerpt
    - Handle overlapping patterns gracefully
  - [x] 2.4 Ensure character-level tests pass
    - Run ONLY the tests written in 2.1

**Acceptance Criteria:**
- `humanise_text()` correctly applies character-level tells based on tier
- Findings are recorded with line numbers and excerpts
- Text without AI tells passes through unchanged
- Tests from 2.1 pass

---

#### Task Group 3: Structural Tell Processing
**Dependencies:** Task Groups 1, 2

- [x] 3.0 Complete structural tell processing
  - [x] 3.1 Write 5-7 focused tests for structural tell detection and rewriting
    - Test filler phrase detection (flagging mode -- no text modification)
    - Test filler phrase rewriting (rewrite mode -- removes filler phrases)
    - Test hedging language detection
    - Test bullet-list-after-single-sentence detection
    - Test uniform paragraph length detection
    - Test repetitive transition word detection
    - Test that structural tells are flag-only when `rewrite` is None
  - [x] 3.2 Implement structural tell detection in `humanise_text()`
    - Structural tells default to flagging-only (recorded in findings but text not modified)
    - When `rewrite` list includes a matching sub-option (or `all`), apply the rewrite
    - Sub-options: `bullet-lists`, `filler-phrases`, `hedging`, `uniform-paragraphs`, `repetitive-transitions`
    - Structural detection may require multi-line context (paragraph-level analysis)
  - [x] 3.3 Implement filler phrase and hedging rewriting logic
    - Filler phrases: remove the phrase, clean up resulting whitespace/capitalisation
    - Hedging language: remove or simplify, clean up sentence structure
  - [x] 3.4 Implement bullet-list restructuring logic
    - Detect single-sentence-then-bullet-list pattern
    - When rewriting: merge into flowing prose or restructure as appropriate
  - [x] 3.5 Implement uniform paragraph and repetitive transition handling
    - Uniform paragraphs: flag with suggestion to vary length
    - Repetitive transitions: flag sequential use of "Furthermore", "Moreover", "Additionally"; when rewriting, vary or remove
  - [x] 3.6 Ensure structural tell tests pass
    - Run ONLY the tests written in 3.1

**Acceptance Criteria:**
- Structural tells are detected and recorded as findings with line numbers
- Without `--rewrite`, structural tells are flagged only (text not modified)
- With `--rewrite all` or specific sub-options, matching structural tells are rewritten
- Tests from 3.1 pass

---

### Reading Age Analysis

#### Task Group 4: Reading Age Calculation and Suggestions
**Dependencies:** Task Group 2 (needs HumaniseResult dataclass)

- [x] 4.0 Complete reading age analysis
  - [x] 4.1 Write 5-7 focused tests for reading age calculation
    - Test Flesch-Kincaid Grade Level calculation on known text
    - Test Gunning Fog Index calculation on known text
    - Test Coleman-Liau Index calculation on known text
    - Test composite score averaging and descriptive level mapping
    - Test per-paragraph suggestion generation when text exceeds target
    - Test numeric target (e.g. 14) and descriptive target (e.g. "general") both work
  - [x] 4.2 Implement readability formulae directly (no external dependency)
    - Implement syllable counting for UK English words
    - Implement Flesch-Kincaid Grade Level
    - Implement Gunning Fog Index
    - Implement Coleman-Liau Index
    - Compute composite score as average of the three
  - [x] 4.3 Implement descriptive level mapping
    - `basic`: age 9-11
    - `general`: age 12-14
    - `advanced`: age 15-17
    - `technical`: age 18+
    - Support both numeric age and descriptive level as input target
  - [x] 4.4 Implement per-paragraph suggestion generation
    - For each paragraph/sentence exceeding the target, generate a suggestion with line number and current grade
    - Format: "Sentence on line N has a Flesch-Kincaid grade of X; consider splitting or simplifying"
  - [x] 4.5 Integrate reading age into `humanise_text()` when `reading_age_target` is provided
    - Populate `reading_age_report` in HumaniseResult with: current age (numeric and descriptive), target, delta, and suggestions list
  - [x] 4.6 Ensure reading age tests pass
    - Run ONLY the tests written in 4.1

**Acceptance Criteria:**
- All three readability formulae produce correct results for known reference texts
- Composite score maps correctly to descriptive levels
- Per-paragraph suggestions identify sentences exceeding target
- Tests from 4.1 pass

---

### Output Modes

#### Task Group 5: Terminal Report, Inline Annotation, and Report-to-Disk
**Dependencies:** Task Groups 2, 3, 4

- [x] 5.0 Complete output modes
  - [x] 5.1 Write 5-7 focused tests for output modes
    - Test terminal report format: grouped by category, includes line numbers, excerpts, counts, severity summary
    - Test terminal report includes reading age section when analysis is present
    - Test inline annotation for .md format (markdown comment markers)
    - Test inline annotation for .py format (# comments)
    - Test inline annotation for .html format (HTML comments)
    - Test report-to-disk writes correct content to file
    - Test that annotations do not break document structure
  - [x] 5.2 Implement terminal report formatter
    - Group findings by category (character-level, structural)
    - Show line numbers and excerpts for each finding
    - Include counts per tell type and severity summary
    - Include reading age section when `--reading-age` is active
    - Output to stderr when processing stdin (stdout reserved for processed text)
  - [x] 5.3 Implement format-aware inline annotation (`--annotate`)
    - `.md`: markdown inline markers (e.g. `<!-- HUMANISE: tell description -->`)
    - `.html`: HTML comments (e.g. `<!-- HUMANISE: tell description -->`)
    - `.py`: Python comments (e.g. `# HUMANISE: tell description`)
    - `.rst`: RST comments (e.g. `.. HUMANISE: tell description`)
    - `.txt`: plain-text brackets (e.g. `[HUMANISE: tell description]`)
    - Insert annotations at the correct line positions without breaking syntax
  - [x] 5.4 Implement report-to-disk (`--report`)
    - Accept optional file path argument
    - Default path: `<input-filename>.humanise-report.txt`
    - Write same content as terminal report to disk
    - Compatible with `--annotate` (both can run together)
  - [x] 5.5 Ensure output mode tests pass
    - Run ONLY the tests written in 5.1

**Acceptance Criteria:**
- Terminal report is well-formatted with grouped findings, counts, and reading age analysis
- Inline annotations are format-aware and do not break document structure
- Report-to-disk writes correct content with sensible default path
- Tests from 5.1 pass

---

### CLI and File Processing Integration

#### Task Group 6: CLI Flags and File Processing Pipeline
**Dependencies:** Task Groups 1-5

- [x] 6.0 Complete CLI integration
  - [x] 6.1 Write 6-8 focused tests for CLI integration
    - Test `--humanise` flag activates humanisation (no spelling conversion unless also specified)
    - Test `--humanise --rewrite all` applies structural rewrites
    - Test `--humanise --level minimal` restricts to character-level tells only
    - Test `--humanise --check` returns exit code 1 when tells found, 0 when clean
    - Test `--humanise --reading-age 14` includes reading age in report
    - Test `--humanise --annotate` inserts inline annotations
    - Test `--humanise --comments-only` for .py files only analyses comments/docstrings
    - Test stdin/stdout streaming with `--humanise`
  - [x] 6.2 Add new CLI arguments to `main()` in `convert.py`
    - `--humanise`: `store_true`, activates AI tell detection
    - `--rewrite`: accepts `all` or comma-separated sub-options; requires `--humanise`
    - `--annotate`: `store_true`, adds inline comments; requires `--humanise`
    - `--level`: choices `minimal`, `moderate`, `full`; default `moderate`; requires `--humanise`
    - `--reading-age`: accepts numeric age or descriptive level; requires `--humanise`
    - `--report`: optional file path; requires `--humanise`
    - Add validation: `--rewrite`, `--annotate`, `--level`, `--reading-age`, `--report` all require `--humanise`
  - [x] 6.3 Implement `humanise_file()` in `humanise.py`
    - Follow `convert_file()` pattern: read file, process, compare, write back
    - Accept parameters: src, dst, level, rewrite, reading_age_target, check, strict, annotate, comments_only
    - For .py files with `--comments-only`, only analyse comments and docstrings
    - Return HumaniseResult
  - [x] 6.4 Implement `humanise_stream()` in `humanise.py`
    - Follow `convert_stream()` generator pattern
    - Buffer lines for structural tells that need multi-line context
    - Terminal report output goes to stderr
  - [x] 6.5 Implement `humanise_paths()` in `humanise.py`
    - Follow `process_paths()` pattern: walk directories, filter by extension, delegate to `humanise_file()`
    - Extend default include extensions to add `.rst` and `.html` when `--humanise` is active
    - Include `.docx` only when optional dependency is available
  - [x] 6.6 Add dispatch logic in `main()` to call `humanise.py` when `--humanise` is present
    - If `--humanise` and no src paths: call `humanise_stream()` on stdin
    - If `--humanise` and src paths: call `humanise_paths()`
    - If `--humanise` combined with spelling conversion flags: run both independently
    - Handle `--check` exit code: 1 if tells detected, 0 if clean
    - Print terminal report after processing
    - Write report to disk if `--report` specified
  - [x] 6.7 Ensure CLI integration tests pass
    - Run ONLY the tests written in 6.1

**Acceptance Criteria:**
- All new CLI flags are parsed and validated correctly
- `--humanise` runs independently of spelling conversion
- File processing pipeline handles all supported text formats
- Streaming works with stdin/stdout, report to stderr
- Check mode returns correct exit codes
- Tests from 6.1 pass

---

### Optional Dependency: DOCX Support

#### Task Group 7: DOCX File Format Support
**Dependencies:** Task Group 6

- [x] 7.0 Complete DOCX support
  - [x] 7.1 Write 3-5 focused tests for DOCX support
    - Test that missing `python-docx` dependency produces a clear error message with install suggestion
    - Test reading text from a .docx file paragraphs and runs
    - Test writing back to .docx preserving formatting after tell application
    - Test inline annotation insertion in .docx (if applicable)
  - [x] 7.2 Add `python-docx` as optional dependency in `pyproject.toml`
    - Add `[project.optional-dependencies]` section with `docx = ["python-docx"]`
    - Or use Poetry extras syntax: add docx extras group
  - [x] 7.3 Implement DOCX reading/writing in `humanise.py`
    - Import `python-docx` with try/except; on ImportError, store a flag
    - When .docx file encountered without dependency: print clear error message suggesting `pip install uwotm8[docx]`
    - Extract text from paragraphs and runs
    - Apply tells to extracted text
    - Write back preserving original formatting (bold, italic, fonts, etc.)
  - [x] 7.4 Ensure DOCX tests pass
    - Run ONLY the tests written in 7.1

**Acceptance Criteria:**
- `pip install uwotm8[docx]` installs python-docx
- Missing dependency produces a helpful error message
- DOCX text extraction and write-back preserves formatting
- Tests from 7.1 pass

---

### Testing and Quality

#### Task Group 8: Test Review, Integration Tests, and Quality Checks
**Dependencies:** Task Groups 1-7

- [x] 8.0 Review existing tests and add integration/end-to-end coverage
  - [x] 8.1 Review all tests from Task Groups 1-7
    - Review tests from tells registry (1.1)
    - Review tests from character-level processing (2.1)
    - Review tests from structural processing (3.1)
    - Review tests from reading age (4.1)
    - Review tests from output modes (5.1)
    - Review tests from CLI integration (6.1)
    - Review tests from DOCX support (7.1)
    - Total existing tests: approximately 34-48 tests
  - [x] 8.2 Analyse test coverage gaps for this feature
    - Identify critical end-to-end workflows lacking coverage
    - Focus on integration between tells registry, processing engine, output modes, and CLI
    - Check that combined flag scenarios are tested (e.g. `--humanise --check --strict`)
  - [x] 8.3 Write up to 10 additional integration tests
    - End-to-end test: `--humanise` on a markdown file with mixed character and structural tells, verify report output
    - End-to-end test: `--humanise --rewrite all --level full` on a file with all tell types, verify correct rewrites
    - End-to-end test: `--humanise --annotate` on each supported format (.md, .py, .html, .rst, .txt), verify annotations inserted correctly
    - End-to-end test: `--humanise --check` returns correct exit codes
    - End-to-end test: `--humanise --reading-age general` produces reading age report with suggestions
    - End-to-end test: combined `--humanise --strict` with spelling conversion runs both independently
    - End-to-end test: stdin/stdout pipeline with `--humanise`
    - Edge case: empty file produces no errors
    - Edge case: file with no AI tells produces clean report
    - Edge case: `--rewrite` without `--humanise` produces validation error
  - [x] 8.4 Run all feature-specific tests
    - Run all tests from groups 1-7 plus new integration tests from 8.3
    - Expected total: approximately 44-58 tests
    - Verify all pass
  - [x] 8.5 Run project quality checks
    - Run `make check` (mypy, ruff, deptry, pre-commit)
    - Fix any type hint issues, linting errors, or import problems
    - Ensure new modules pass mypy with `disallow_untyped_defs = True`
  - [x] 8.6 Run full existing test suite to verify no regressions
    - Run `make test` to ensure existing `test_convert.py` tests still pass
    - Verify no breaking changes to existing CLI behaviour

**Acceptance Criteria:**
- All feature-specific tests pass (approximately 44-58 tests total)
- All integration/end-to-end tests pass
- `make check` passes with no errors
- Existing test suite passes with no regressions
- No more than 10 additional tests added in this group

---

## Execution Order

Recommended implementation sequence:

1. **Task Group 1: Tells Registry** -- Foundation data model, no dependencies
2. **Task Group 2: Character-Level Processing** -- Core engine, depends on registry
3. **Task Group 3: Structural Processing** -- Extends core engine with multi-line analysis
4. **Task Group 4: Reading Age Analysis** -- Independent calculation module, needs HumaniseResult from Group 2
5. **Task Group 5: Output Modes** -- Formats results from Groups 2-4 for display
6. **Task Group 6: CLI Integration** -- Wires everything together via command-line flags
7. **Task Group 7: DOCX Support** -- Optional format support, extends file processing pipeline
8. **Task Group 8: Integration Testing and Quality** -- Final validation across all components

Note: Task Groups 3 and 4 can be developed in parallel as they are independent of each other (both depend on Group 2 but not on each other).

## Key Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `uwotm8/tells.py` | Create | Tell dataclass, enums, registry list, tier filtering |
| `uwotm8/humanise.py` | Create | Core processing engine, file/stream/paths functions, reading age |
| `uwotm8/convert.py` | Modify | Add CLI flags, dispatch to humanise.py |
| `pyproject.toml` | Modify | Add python-docx optional dependency |
| `tests/test_tells.py` | Create | Tests for tells registry |
| `tests/test_humanise.py` | Create | Tests for humanise processing, output modes, reading age |
| `tests/test_humanise_cli.py` | Create | Tests for CLI integration |
| `tests/test_humanise_docx.py` | Create | Tests for DOCX support |
| `tests/test_humanise_integration.py` | Create | End-to-end integration tests |
