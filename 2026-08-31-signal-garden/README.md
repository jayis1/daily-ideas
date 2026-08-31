# Signal Garden

Signal Garden turns text into deterministic terminal art. Each distinct word becomes a signal flower with a hash-derived symbol and strength, plus a repeatable phase that determines where it rises above the waveform. It is a small, dependency-free CLI for exploring text, making reproducible terminal keepsakes, and exporting data for other tools.

## Features

- Extracts Unicode words and preserves first-seen order.
- Normalizes case, removes surrounding punctuation, and keeps useful inner apostrophes and hyphens.
- Deduplicates repeated words.
- Produces stable output for the same text; `--seed` lets you choose the phase pattern.
- Renders a bordered Unicode waveform with stems, symbols, and labels.
- Validates canvas dimensions before rendering.
- Reports the number of signals and strongest word.
- Optionally prints total and average strength with `--stats`.
- Exports a self-describing JSON document containing signals and aggregate statistics.
- Supports `--help` and `--version`.
- Uses only the Python standard library at runtime.

## Requirements and installation

Python 3.8 or newer is required. There are no packages to install. Clone the collection, then run the script from this directory:

```bash
cd 2026-08-31-signal-garden
python3 signal_garden.py --help
```

## Usage

Pass text as one or more arguments:

```bash
python3 signal_garden.py "the moon remembers every river"
```

When no text arguments are supplied, Signal Garden reads one sentence from standard input. This works well in a pipeline and avoids an interactive prompt in scripts:

```bash
echo "rain on glass" | python3 signal_garden.py --seed 12
```

Use a fixed seed and custom dimensions for reproducible art:

```bash
python3 signal_garden.py moon river moon --seed 7 --width 50 --height 12
```

Show aggregate strength statistics:

```bash
python3 signal_garden.py "quiet signals grow" --stats
```

Export the analysis. Parent directories are created when necessary:

```bash
python3 signal_garden.py "rain on glass" --seed 12 --json exports/rain.json
```

Inspect the available options and version:

```bash
python3 signal_garden.py --help
python3 signal_garden.py --version
```

The canvas must be at least 24 columns wide and 6 rows high. Invalid dimensions are reported as command-line errors instead of producing a partial drawing.

## JSON format

An export contains the original text, the tool version, a summary, and one object per distinct word:

```json
{
  "version": "1.1.0",
  "text": "rain on glass",
  "summary": {
    "unique_signals": 3,
    "total_strength": 17,
    "average_strength": 5.67,
    "strongest": "glass"
  },
  "signals": [
    {"word": "rain", "strength": 6, "phase": 3, "symbol": "✺"}
  ]
}
```

The exact values depend on the input and seed. The `signals` array can be consumed without parsing the terminal rendering.

## How it works

Words are extracted with a Unicode-aware regular expression. Each word is hashed with SHA-256: one byte selects a strength from 2 through 9 and another selects a flower symbol. A local pseudo-random generator assigns each signal a phase from 0 through 7. Without `--seed`, the generator seed is derived from the full input text, making runs reproducible. With a seed, only the phases change; word-derived symbols and strengths remain stable.

The renderer places flowers across a horizontal baseline. Their strength controls vertical amplitude, their phase controls the sine-wave position, and a stem connects each flower to the baseline.

## Testing

Run the project tests with pytest:

```bash
python3 -m pytest -q
```

The suite covers deterministic deduplication, Unicode tokenization, canvas validation, empty-input summaries, CLI statistics, nested JSON export, and version output.

## Project files

```text
signal_garden.py       # CLI, analysis engine, renderer, and JSON export
 test_signal_garden.py  # unit and subprocess tests
 README.md             # usage and implementation notes
```

Signal Garden is an art and text-exploration toy, not a linguistic or statistical analysis tool.
