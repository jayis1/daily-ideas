# Keyboard Heatmap Analyzer

Keyboard Heatmap Analyzer is a small Python CLI that turns text into a keyboard-shaped usage report for a US QWERTY layout. It can inspect inline text, files, presets, or piped stdin and then summarize key frequency, row/hand/finger balance, and a few ergonomic heuristics.

## Features

- Keyboard-shaped terminal heatmap
- Works with direct text, `--file`, `--preset`, and stdin
- JSON output via `--json`
- Row, hand, and finger usage summaries
- Bigram analysis, including same-finger and row-jump hotspots
- Approximate effort scoring for quick ergonomic comparisons
- `--help` and `--version` support
- Test suite with CLI and edge-case coverage

## What was fixed in this bug-hunt pass

- Fixed a crash when analyzing `~` / backtick input
- Added the backtick key to the rendered keyboard layout and key metadata
- Fixed unhandled file read failures for special or unreadable paths so the CLI now exits with a clean error message instead of a traceback
- Expanded tests to cover both regressions
- Bumped the CLI version to `1.1.1`

## Requirements

- Python 3.11+
- `pytest` if you want to run tests

The application itself uses only the Python standard library.

## Installation

```bash
cd ~/daily-ideas/2026-08-22-keyboard-heatmap-analyzer
python3 -m pip install pytest  # optional, for tests only
```

## How to run

### Analyze direct text

```bash
python3 keyboard_heatmap.py "the quick brown fox jumps over the lazy dog"
```

### Analyze a file

```bash
python3 keyboard_heatmap.py --file README.md
```

### Analyze a built-in preset

```bash
python3 keyboard_heatmap.py --preset pangram
```

### Read from stdin

```bash
echo "vim motions meet midnight poetry" | python3 keyboard_heatmap.py --stdin --no-color
```

If stdin is piped and no other input source is provided, the tool reads it automatically.

### Emit JSON

```bash
python3 keyboard_heatmap.py --json --preset code
```

## CLI usage

```text
usage: keyboard_heatmap.py [-h] [--file FILE] [--preset {code,pangram,poem}] [--stdin] [--top TOP] [--json] [--no-color] [--version] [text ...]
```

## Options

- `text` — free-form text to analyze
- `--file FILE` — read UTF-8 text from a file
- `--preset {code,pangram,poem}` — analyze a built-in sample
- `--stdin` — explicitly include standard input as an input source
- `--top TOP` — number of top items shown in the report
- `--json` — print JSON instead of the human-readable heatmap/report
- `--no-color` — disable ANSI colors
- `--version` — print version and exit
- `-h, --help` — show help

## Usage examples

### Human-readable report

```bash
python3 keyboard_heatmap.py --preset poem --no-color
```

### Inspect punctuation-heavy input

```bash
python3 keyboard_heatmap.py '~![]{}()' --no-color
```

### Save structured metrics

```bash
python3 keyboard_heatmap.py --json "hello keyboard world" > analysis.json
```

### Analyze this project source

```bash
python3 keyboard_heatmap.py --file keyboard_heatmap.py --top 5
```

## Output summary

Human-readable mode prints:

- a keyboard-shaped count table
- input and mapped totals
- ergonomic summary metrics
- row and hand usage
- finger hotspots
- top keys and bigrams
- unmapped characters, when present

JSON mode returns raw counters plus derived summary metrics such as:

- top keys
- top bigrams
- hand alternation percent
- same-finger percent
- row-jump percent
- effort per 100 keys

## Running tests

```bash
pytest -q
```

## Known issues

- The layout model is intentionally approximate and assumes a US QWERTY keyboard.
- The ergonomic score is a heuristic for comparison, not a scientific measurement.
- Non-keyboard Unicode characters are reported as unmapped rather than transliterated.

## Changelog

### 1.1.1

- Added backtick support to match the existing shifted `~` normalization
- Prevented crashes on `~` input
- Replaced raw traceback behavior for unreadable/special files with user-facing error messages
- Added regression tests for both fixes

### 1.1.0

- Added JSON output
- Added stdin support and automatic piped-input detection
- Added ergonomic summary metrics and expanded documentation
