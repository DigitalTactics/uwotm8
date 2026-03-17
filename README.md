# uwotm8

[![Release](https://img.shields.io/github/v/release/DigitalTactics/uwotm8)](https://img.shields.io/github/v/release/DigitalTactics/uwotm8)
[![Build status](https://img.shields.io/github/actions/workflow/status/DigitalTactics/uwotm8/main.yml?branch=main)](https://github.com/DigitalTactics/uwotm8/actions/workflows/main.yml?query=branch%3Amain)
[![License](https://img.shields.io/github/license/DigitalTactics/uwotm8)](https://img.shields.io/github/license/DigitalTactics/uwotm8)

A tool to convert American English spelling to British English and remove common AI-generated text patterns to make content feel more naturally human-written.

- **Github repository**: <https://github.com/DigitalTactics/uwotm8/>
- **Documentation** <https://digitaltactics.github.io/uwotm8/>

## Installation

```bash
pip install uwotm8
```

## Quick Start

Convert a single file:

```bash
uwotm8 example.txt
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

en_gb_str = convert_american_to_british_spelling("Our American neighbors' dialog can be a bit off-color.")
print(en_gb_str)
# Output: "Our American neighbours' dialogue can be a bit off-colour."
```

## Features

- Converts common American English spellings to British English
- Preserves words in special contexts (code blocks, URLs, hyphenated terms)
- Maintains an ignore list of technical terms that shouldn't be converted
- Preserves original capitalization patterns
- Supports Python file mode to convert only comments and docstrings, leaving code unchanged

### AI Tell Removal (`--humanise`)

The `--humanise` flag detects and removes common patterns found in AI-generated text, making content feel more naturally human-written for a general audience. This includes:

- Replacing em dashes, smart quotes, non-breaking spaces, and other Unicode artefacts with standard equivalents
- Detecting filler phrases, hedging language, and repetitive transitions
- Flagging structural patterns like single-sentence-then-bullet-list overuse
- Reading age analysis with configurable targets (numeric or descriptive)
- Multiple output modes: terminal report, inline annotations, and save-to-disk

> **Note:** The purpose of the `--humanise` feature is to improve readability and remove stylistic artefacts commonly produced by AI text generation. It is not intended to obfuscate the origin of AI-generated content or to deceive readers about how text was produced. The goal is to make content more human-friendly for the end reader.

```bash
# Flag AI tells in a markdown file
uwotm8 --humanise report.md

# Automatically rewrite structural patterns
uwotm8 --humanise --rewrite all --level full docs/

# Analyse reading age and get simplification suggestions
uwotm8 --humanise --reading-age general report.md

# Combine with spelling conversion
uwotm8 --humanise --strict src/
```

For full documentation, examples, and advanced usage, please visit the [documentation site](https://digitaltactics.github.io/uwotm8/).

---

Originally forked from [i-dot-ai/uwotm8](https://github.com/i-dot-ai/uwotm8). Repository initiated with [fpgmaas/cookiecutter-poetry](https://github.com/fpgmaas/cookiecutter-poetry).
