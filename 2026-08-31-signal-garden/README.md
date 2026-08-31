# Signal Garden

Signal Garden is a tiny terminal visualization that turns a sentence into a living-looking ASCII waveform. Each distinct word becomes a signal flower: its hash determines the flower symbol and strength, while a seed controls its phase. The same text and seed always produce the same garden, making it useful for little text-based keepsakes, demos, and reproducible terminal art.

## Features

- Converts words into deterministic signal objects.
- Deduplicates repeated words while preserving their first appearance.
- Renders a bordered Unicode waveform with labeled signal flowers.
- Supports custom canvas dimensions and reproducible `--seed` values.
- Exports the analyzed signal data as readable JSON.
- Uses only Python's standard library at runtime.

## Installation

Python 3.8 or newer is required. No package installation is needed:

```bash
cd 2026-08-31-signal-garden
python3 signal_garden.py --help
```

## Running

Pass a sentence as arguments:

```bash
python3 signal_garden.py "the moon remembers every river"
```

If no text is supplied, the program prompts for a sentence:

```bash
python3 signal_garden.py
```

Use a fixed seed and a compact canvas for reproducible output:

```bash
python3 signal_garden.py moon river moon --seed 7 --width 50 --height 12
```

The `--width` value must be an integer; for example:

```bash
python3 signal_garden.py moon river moon --seed 7 --width 50 --height 12
```

Save the underlying signals while rendering:

```bash
python3 signal_garden.py "rain on glass" --seed 12 --json rain.json
```

## What it does

The input is normalized to lowercase and punctuation around words is removed. Each first-seen word is hashed with SHA-256. Bytes from that hash select a flower symbol and a strength from 2 to 9. A local pseudo-random generator assigns a phase to each word; the optional seed controls that generator. The renderer places the signals across a horizontal baseline and draws their vertical stems. It then prints the number of unique signals and the strongest word.

The JSON export contains the original text and an array of `word`, `strength`, `phase`, and `symbol` fields, so another program can remix the garden without parsing terminal art.

## Testing

From the project directory:

```bash
python3 -m pytest -q
```

The tests cover deterministic analysis, duplicate removal, rendering dimensions, canvas validation, and exported data shape.
