# Keyboard Heatmap Analyzer

Keyboard Heatmap Analyzer is a dependency-free Python CLI that turns text into a keyboard-shaped usage map. Feed it prose, code, logs, or piped stdin and it will show which QWERTY keys get hammered most, how balanced the typing pattern is, and where awkward finger travel appears.

## What it does

The tool normalizes text onto a US QWERTY layout, then reports:

- per-key frequencies rendered as a terminal heatmap
- row, hand, and finger usage totals
- top keys and bigrams
- same-finger bigrams that may feel awkward to type
- row-jump bigrams that indicate more finger travel
- an approximate ergonomic effort score
- optional JSON output for scripting and further analysis

It is useful for quickly inspecting:

- writing style differences between prose and code
- ergonomic hotspots in generated text
- keyboard patterns in datasets or logs
- terminal demos and teaching material about typing patterns

## Features

- Pure Python, standard library only
- ANSI-colored terminal heatmap
- Works with inline text, files, presets, and stdin
- `--json` output for automation
- Ergonomic summary with effort, hand alternation, same-finger share, and row-jump share
- Built-in demo presets for quick exploration
- `--help` and `--version` CLI support
- Automated tests with pytest

## Project files

- `keyboard_heatmap.py` — main CLI application
- `test_keyboard_heatmap.py` — tests for analysis and CLI behavior
- `README.md` — documentation

## Requirements

- Python 3.11+ recommended
- `pytest` only if you want to run the test suite

## Installation

```bash
cd ~/daily-ideas/2026-08-22-keyboard-heatmap-analyzer
python3 -m pip install pytest  # optional
```

The application itself has no external dependencies.

## How to run

### Analyze direct text

```bash
python3 keyboard_heatmap.py "the quick brown fox jumps over the lazy dog"
```

### Analyze a file

```bash
python3 keyboard_heatmap.py --file README.md
```

### Use a built-in preset

```bash
python3 keyboard_heatmap.py --preset pangram
```

### Read from stdin

```bash
echo "vim motions meet midnight poetry" | python3 keyboard_heatmap.py --stdin --no-color
```

If stdin is piped in and no other input source is given, the tool will read it automatically.

### Emit JSON for another tool

```bash
python3 keyboard_heatmap.py --json --preset code
```

## CLI usage

```text
usage: keyboard_heatmap.py [-h] [--file FILE] [--preset {code,pangram,poem}] [--stdin] [--top TOP] [--json] [--no-color] [--version] [text ...]
```

### Arguments and options

- `text` — free-form text to analyze
- `--file FILE` — read UTF-8 text from a file
- `--preset {code,pangram,poem}` — analyze a built-in sample
- `--stdin` — explicitly include standard input as a source
- `--top TOP` — number of top items shown in reports
- `--json` — print structured JSON instead of the human-readable report
- `--no-color` — disable ANSI colors
- `--version` — print the program version and exit
- `-h, --help` — show help text

## Example workflows

### 1. Inspect a source file for typing hotspots

```bash
python3 keyboard_heatmap.py --file keyboard_heatmap.py --top 5
```

This prints the heatmap plus a report showing the busiest keys, row distribution, finger hotspots, and common bigrams.

### 2. Compare prose-like input with code-like input manually

```bash
python3 keyboard_heatmap.py --preset poem --no-color
python3 keyboard_heatmap.py --preset code --no-color
```

You can quickly see differences in punctuation use, space share, hand balance, and same-finger patterns.

### 3. Pipe into jq or save metrics

```bash
python3 keyboard_heatmap.py --json "hello keyboard world" > analysis.json
```

The JSON output includes raw counts and a summary block with top keys, top bigrams, hand alternation percentage, row-jump percentage, and effort per 100 keys.

## Example output

Human-readable mode prints:

- a keyboard-shaped count table
- input and mapped totals
- ergonomic summary metrics
- row and hand balance tables
- finger hotspots
- top keys and bigrams
- unmapped characters, if any

JSON mode prints a structured object containing the full analysis and derived summary metrics.

## Running tests

```bash
pytest -q
```

## Notes on the ergonomic score

The effort score is an approximate heuristic, not a medical or scientific measure. It weights home-row usage as cheaper than number-row or pinky-heavy usage, which makes it useful for relative comparisons between texts.

## Why this project is interesting

Most frequency analyzers stop at histograms. This project maps statistics back onto the physical keyboard, which makes typing behavior much easier to spot visually. Poetry, command lines, and source code all produce distinct heat signatures, and the ergonomic summary makes those differences easier to reason about.
