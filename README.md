# uwotm8

[![Release](https://img.shields.io/github/v/release/DigitalTactics/uwotm8)](https://img.shields.io/github/v/release/DigitalTactics/uwotm8)
[![Build status](https://img.shields.io/github/actions/workflow/status/DigitalTactics/uwotm8/main.yml?branch=main)](https://github.com/DigitalTactics/uwotm8/actions/workflows/main.yml?query=branch%3Amain)
[![License](https://img.shields.io/github/license/DigitalTactics/uwotm8)](https://img.shields.io/github/license/DigitalTactics/uwotm8)

A tool to convert American English spelling to British English and remove common AI-generated text patterns to make content feel more naturally human-written.

- **Github repository**: <https://github.com/DigitalTactics/uwotm8/>
- **Documentation**: <https://digitaltactics.github.io/uwotm8/>

## Installation

Install from GitHub:

```bash
pip install git+https://github.com/DigitalTactics/uwotm8.git
```

With optional `.docx` file support:

```bash
pip install "uwotm8[docx] @ git+https://github.com/DigitalTactics/uwotm8.git"
```

## Quick Start

### Spelling Conversion

Convert American English to British English in a file:

```bash
uwotm8 example.txt
```

Convert an entire directory:

```bash
uwotm8 src/
```

Convert only comments and docstrings in Python files:

```bash
uwotm8 --comments-only my_script.py
```

Read from stdin and write to stdout:

```bash
echo "I love the color gray." | uwotm8
# Output: "I love the colour grey."
```

Use in Python code:

```python
from uwotm8 import convert_american_to_british_spelling

text = convert_american_to_british_spelling("Our American neighbors' dialog can be a bit off-color.")
print(text)
# Output: "Our American neighbours' dialogue can be a bit off-colour."
```

### AI Tell Removal

Detect AI-generated text patterns and get a report:

```bash
uwotm8 --humanise report.md
```

Automatically rewrite structural patterns:

```bash
uwotm8 --humanise --rewrite all docs/
```

Choose aggressiveness level (`minimal`, `moderate`, or `full`):

```bash
uwotm8 --humanise --level full report.md
```

Get reading age analysis with a target:

```bash
uwotm8 --humanise --reading-age general report.md
uwotm8 --humanise --reading-age 14 report.md
```

Add inline annotations to the source file:

```bash
uwotm8 --humanise --annotate report.md
```

Save the report to disk:

```bash
uwotm8 --humanise --report findings.txt report.md
```

Combine spelling conversion and humanisation:

```bash
uwotm8 --humanise --strict src/
```

Use in Python code:

```python
from uwotm8.humanise import humanise_text

result = humanise_text("It\u2019s important to note that\u2014in today\u2019s world\u2014we must adapt.")
print(result.text)
# Output: "It's important to note that, in today's world, we must adapt."
print(result.findings)
# Lists detected AI tells with line numbers and descriptions
```

## Features

### Spelling Conversion

- Converts common American English spellings to British English
- Preserves words in special contexts (code blocks, URLs, hyphenated terms)
- Maintains an ignore list of technical terms that shouldn't be converted
- Preserves original capitalisation patterns
- Supports Python file mode to convert only comments and docstrings, leaving code unchanged

### AI Tell Removal (`--humanise`)

The `--humanise` flag detects and removes common patterns found in AI-generated text, making content feel more naturally human-written for a general audience.

**Character-level fixes:**
- Em dashes and en dashes replaced with commas or standard hyphens
- Smart quotes normalised to straight quotes
- Non-breaking spaces and zero-width characters removed
- Unicode ellipsis, fancy bullets, and other artefacts normalised
- Excessively long italic spans stripped

**Bold text handling:**

AI-generated text tends to overuse bold formatting in distinctive ways. The tool applies context-aware rules to handle bold text differently depending on where it appears:

| Context | Before | After | Rule |
|---------|--------|-------|------|
| Bold paragraph opener | `**Remote work is here.** More text` | `Remote work is here: More text` | Strip bold, replace full stop with colon |
| Bold pseudo-heading | `**Key Benefits**` | `### Key Benefits` | Convert to next available heading level (h1-h6) |
| Mid-sentence bold | `showed **strong growth** in` | `showed *strong growth* in` | Convert to italic |
| End-of-sentence bold | `achieved **record results**.` | `achieved *record results*.` | Convert to italic |
| Bullet-item bold | `- **Revenue** grew` | `- Revenue grew` | Strip bold entirely |

Bold pseudo-headings are detected by checking whether the bold text is short (under 10 words), in title case, has no sentence-ending punctuation, and is the only text on its line. When converted, the heading level is set to one below the lowest unused level already in the document (e.g. if h1-h3 exist, the pseudo-heading becomes h4).

**Structural pattern detection:**
- Filler phrases ("It's important to note that", "In today's world", "Let's dive in")
- Hedging language ("It's worth noting", "arguably", "one might say")
- Single-sentence-then-bullet-list overuse
- Uniform paragraph lengths
- Repetitive transitions ("Furthermore", "Moreover", "Additionally" in sequence)

Structural patterns are flagged by default. Use `--rewrite` to opt in to automatic rewriting:

```bash
# Rewrite all structural patterns
uwotm8 --humanise --rewrite all docs/

# Rewrite only specific patterns
uwotm8 --humanise --rewrite filler-phrases,hedging report.md
```

Available rewrite sub-options: `all`, `bullet-lists`, `filler-phrases`, `hedging`, `uniform-paragraphs`, `repetitive-transitions`.

**Aggressiveness levels:**

| Level | What it covers |
|-------|---------------|
| `minimal` | Non-breaking spaces, zero-width chars, smart quotes, Unicode normalisation |
| `moderate` (default) | Everything in minimal, plus em dashes, bold text handling (openers, pseudo-headings, mid/end-sentence to italic, bullet-item stripping), long italic stripping, filler phrases, hedging |
| `full` | Everything in moderate, plus bullet list restructuring, paragraph uniformity, repetitive transitions |

**Reading age analysis:**

Calculates readability using Flesch-Kincaid, Gunning Fog, and Coleman-Liau indices. Set a target as a numeric age or descriptive level:

| Level | Age range |
|-------|-----------|
| `basic` | 9-11 |
| `general` | 12-14 |
| `advanced` | 15-17 |
| `technical` | 18+ |

**Output modes:**
- Terminal report (default) -- grouped findings with line numbers, counts, and severity
- Inline annotations (`--annotate`) -- format-aware comments inserted into the source file
- Save to disk (`--report [path]`) -- write the report to a file

### Supported File Formats

| Format | Spelling | Humanise | Notes |
|--------|----------|----------|-------|
| `.txt` | Yes | Yes | |
| `.md` | Yes | Yes | |
| `.py` | Yes | Yes | `--comments-only` available |
| `.rst` | No | Yes | |
| `.html` | No | Yes | |
| `.docx` | No | Yes | Requires `pip install uwotm8[docx]` |
| stdin/stdout | Yes | Yes | |

## CLI Reference

```
uwotm8 [options] [paths...]

Spelling options:
  --strict              Use strict spelling conversion
  --check               Dry-run mode (exit code 1 if changes needed)
  --comments-only       Convert only comments and docstrings in .py files
  --include EXTS        File extensions to include (default: .py .txt .md)
  --exclude EXTS        File extensions to exclude
  -o, --output PATH     Output file path

Humanise options:
  --humanise            Activate AI tell detection and removal
  --rewrite OPTS        Rewrite structural patterns (all or comma-separated list)
  --annotate            Insert inline annotations in source files
  --level LEVEL         Aggressiveness: minimal, moderate (default), full
  --reading-age TARGET  Reading age target (numeric age or: basic, general, advanced, technical)
  --report [PATH]       Save report to disk (default: <filename>.humanise-report.txt)
```

> **Note:** The purpose of the `--humanise` feature is to improve readability and remove stylistic artefacts commonly produced by AI text generation. It is not intended to obfuscate the origin of AI-generated content or to deceive readers about how text was produced. The goal is to make content more human-friendly for the end reader.

---

Originally forked from [i-dot-ai/uwotm8](https://github.com/i-dot-ai/uwotm8). Repository initiated with [fpgmaas/cookiecutter-poetry](https://github.com/fpgmaas/cookiecutter-poetry).
