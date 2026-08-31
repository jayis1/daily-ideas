# Signal Garden

Signal Garden is a dependency-free Python CLI that turns text into deterministic Unicode terminal art. Each distinct word becomes a signal flower: its SHA-256 hash selects a symbol and strength, while a repeatable phase places it on a waveform. It is intended for text exploration, reproducible terminal keepsakes, and machine-readable exports—not linguistic analysis.

## Features

- Unicode-aware word extraction with surrounding punctuation removed.
- Preserves useful inner apostrophes and hyphens, such as `don't` and `well-known`.
- NFC-normalizes Unicode, so composed and decomposed spellings such as `café` and `café` are treated equivalently.
- Lowercases and deduplicates words while preserving first-seen order.
- Deterministic output for the same input; `--seed` selects a reproducible phase pattern.
- Bordered waveform rendering with stems, symbols, and labels.
- Configurable canvas dimensions with validation.
- Summary output plus optional total and average strength statistics.
- JSON export containing the original text, version, summary, and signal records.
- `--help` and `--version` flags.
- Python standard library only.

## Requirements and installation

Python 3.8 or newer is required. No package installation is needed. From the repository checkout:

```bash
cd 2026-08-31-signal-garden
python3 signal_garden.py --help
```

## Usage

Pass text as one or more arguments:

```bash
python3 signal_garden.py "the moon remembers every river"
```

With no positional text, input is read from standard input:

```bash
echo "rain on glass" | python3 signal_garden.py --seed 12
```

Use a fixed seed and custom dimensions:

```bash
python3 signal_garden.py moon river moon --seed 7 --width 50 --height 12
```

Print aggregate strength statistics:

```bash
python3 signal_garden.py "quiet signals grow" --stats
```

Export JSON; missing parent directories are created automatically:

```bash
python3 signal_garden.py "rain on glass" --seed 12 --json exports/rain.json
```

Inspect options and version:

```bash
python3 signal_garden.py --help
python3 signal_garden.py --version
```

The canvas must be at least 24 columns wide and 6 rows high. To pass text beginning with a dash, use `--` before the text:

```bash
python3 signal_garden.py -- --quiet
```

## Output and JSON format

The terminal output contains the bordered canvas, a count of unique signals, and the strongest word. `--stats` adds total and average strength. An export has this shape:

```json
{
  "version": "1.1.1",
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

Exact signal values depend on the input and seed. The `signals` array can be consumed without parsing terminal art.

## How it works

Words are NFC-normalized and extracted with a Unicode-aware regular expression. Each word is hashed with SHA-256: one byte selects a strength from 2 through 9 and another selects a flower symbol. A local pseudo-random generator assigns each signal a phase from 0 through 7. Without `--seed`, the generator seed is derived from the complete input text; with a seed, only phases change.

The renderer places flowers across a horizontal baseline. Strength controls vertical amplitude, phase controls the sine-wave position, and a stem connects each flower to the baseline.

## Testing

Run the project tests with pytest:

```bash
python3 -m pytest -q
```

The tests cover deterministic analysis, deduplication, Unicode punctuation, canonical Unicode equivalence, canvas validation, empty input, CLI statistics, nested JSON export, and version output.

## Known limitations

- Rendering measures Python characters rather than terminal display-cell width, so some terminals may align wide East Asian glyphs imperfectly.
- Very many distinct words can cause nearby labels to overlap because the canvas is intentionally compact.
- The tool does not provide linguistic stemming, transliteration, or statistical meaning analysis.

## Changelog

### 1.1.1 — bug fixes

- NFC-normalized input before tokenization so combining accents are not silently dropped and canonically equivalent words deduplicate correctly.
- Replaced Python 3.9-only generic type syntax with `typing` equivalents, making the documented Python 3.8 minimum accurate.

### 1.1.0

- Added robust CLI options, statistics, nested JSON export, Unicode tokenization, and expanded tests.
