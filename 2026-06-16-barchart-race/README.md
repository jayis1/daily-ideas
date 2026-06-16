# Barchart Race — Animated ASCII Bar Chart Race Visualizer

Watch values compete and rankings shift over time with smooth ASCII animations. Supports multiple data sources, transformation modes, HTML export, and more.

## Features

- **Animated ASCII bar chart races** in your terminal with smooth interpolation
- **5 built-in datasets**: tech revenue, Olympic medals, programming languages, world population, crypto market cap
- **Custom data**: load CSV or JSON files
- **Random data generation**: quick demos with `--random`
- **Percentage mode** (`--percent`): show each series as share of total (market share)
- **Growth mode** (`--growth`): show percentage change from first period
- **Side-by-side comparison** (`--compare`): compare any two time periods with change arrows and stats table
- **Compact ticker** (`--ticker`): one-line scrolling summary per period
- **Animated HTML export** (`--html`): self-contained HTML file with CSS transitions and play/pause controls
- **Frame export** (`--export`): export individual frames as text files
- **ASCII movie export** (`--export-movie`): single text file with form-feed separators
- **Statistics** (`--stats`): per-series stats with Unicode sparklines, growth ranking, and correlation analysis
- **Final ranking** (`--solve`): show end-state ranking without animation
- **Consistent colors**: each series keeps its color across all frames
- **Configurable**: speed, top-N filtering, color/no-color, loop control

## Installation

No dependencies beyond Python 3.6+ standard library. Just clone and run:

```bash
git clone <repo-url>
cd barchart-race
python3 barchart_race.py --help
```

## Usage

### Basic

```bash
# Default: tech company revenue demo
python3 barchart_race.py

# Choose a built-in dataset
python3 barchart_race.py --sample olympic-medals
python3 barchart_race.py --sample programming-languages
python3 barchart_race.py --sample world-population
python3 barchart_race.py --sample crypto-marketcap

# Load custom data
python3 barchart_race.py --data my_data.csv
python3 barchart_race.py --data my_data.json

# Generate random race
python3 barchart_race.py --random
python3 barchart_race.py --random --seed 42
```

### Display Options

```bash
# Show only top 5 bars
python3 barchart_race.py --top 5

# Faster or slower animation (frames/sec)
python3 barchart_race.py --speed 4
python3 barchart_race.py --speed 0.5

# Don't loop the animation
python3 barchart_race.py --no-loop

# Disable colors
python3 barchart_race.py --no-color

# Compact display mode
python3 barchart_race.py --minimal
```

### Transformation Modes

```bash
# Percentage mode — each series as share of total (market share)
python3 barchart_race.py --percent

# Growth mode — percentage change from first period
python3 barchart_race.py --growth
```

### Analysis

```bash
# Side-by-side comparison of two periods
python3 barchart_race.py --compare 0 -1      # first vs last
python3 barchart_race.py --compare 0 5       # first vs period 5

# Statistics with sparklines
python3 barchart_race.py --stats

# Final ranking (no animation)
python3 barchart_race.py --solve
```

### Export

```bash
# Animated HTML file (open in browser)
python3 barchart_race.py --html output.html

# HTML with custom speed
python3 barchart_race.py --html output.html --speed 3

# Export frames as text files
python3 barchart_race.py --export frames/

# Export as single text file
python3 barchart_race.py --export-movie movie.txt
```

### Other

```bash
# List available datasets
python3 barchart_race.py --list

# Version
python3 barchart_race.py --version

# Help
python3 barchart_race.py --help
```

## Data Formats

### CSV

```csv
label,Apple,Microsoft,Google
Q1,65,45,40
Q2,68,48,43
Q3,72,52,46
```

### JSON

```json
{
  "title": "My Chart",
  "unit": "$",
  "data": {
    "Apple": [65, 68, 72],
    "Microsoft": [45, 48, 52],
    "Google": [40, 43, 46]
  },
  "labels": ["Q1", "Q2", "Q3"]
}
```

## Example Output

### Final Ranking
```
=== Final Ranking: Tech Company Revenue ($B) ===

 🥇  1. Apple  ██████████████████████████████ 150.0$B
 🥈  2. Amazon  ████████████████████████ 120.0$B
 🥉  3. NVIDIA  ████████████████████████ 120.0$B
    4. Microsoft  ███████████████████████ 115.0$B

 Biggest gainer: NVIDIA (112.0$B change)
 Biggest loser:  Intel (6.0$B change)
```

### Statistics with Sparklines
```
  Series          Min      Max     Mean   Growth        Trend
  ─────────── ──────── ──────── ──────── ──────── ────────────
  Apple         65.0    150.0    101.2    +85.0 ▁▁▁▂▂▂▃▃▄▅▅▆
  NVIDIA         8.0    120.0     45.4   +112.0 ▁▁▁▁▁▁▂▃▃▄▅▅
```

### Comparison
```
  Comparing: Q1'21 vs Q2'24

 #1 Apple    ████████ → ████████████████████  ↑+85.0$B
 #2 Amazon   ████ → ████████████████  ↑+85.0$B
 #3 NVIDIA   █ → ████████████████  ↑+112.0$B

  Series         From        To      Change        %
  ─────────── ────────── ────────── ────────── ────────
  Apple        65.0$B    150.0$B     85.0$B  +130.8%
  NVIDIA        8.0$B    120.0$B    112.0$B +1400.0%
```

## Tests

```bash
python3 test_barchart_race.py
```

47 tests covering all features, edge cases, and bug fixes.

## Changelog

### v2.1.0 — Bug Fixes
- **[SECURITY]** Fixed XSS vulnerability in HTML export: series names and labels containing HTML tags are now properly escaped
- **[BUG]** Fixed ticker truncation breaking ANSI escape codes when terminal width is narrow — now truncates by visible characters only and appends RESET code
- **[BUG]** Fixed `ZeroDivisionError` when `--speed 0` is passed — CLI now rejects zero/negative speed with a clear error message
- **[BUG]** Fixed `ZeroDivisionError` in `export_frames()` when `num_steps=1` — now correctly handles single-step export
- **[BUG]** Fixed `load_json()` accepting empty data dict `{}` without error — now raises `ValueError`
- **[BUG]** Fixed `load_csv()` creating empty data dict when CSV has no data columns — now raises `ValueError`
- **[BUG]** Fixed `generate_random_data()` with `num_periods=0` producing 1 value instead of 0 (off-by-one)
- **[BUG]** Fixed `format_value()` showing `-0.00` for very small negative values — now displays `0.00`

### v2.0.0 — Feature Update
- Added percentage mode, growth mode, comparison view, ticker, HTML export, sparklines in stats
- Color-by-name consistency across frames
- 16 new tests

### v1.0.0 — Initial Release
- Animated ASCII bar chart race
- CSV/JSON data loading
- 5 built-in datasets
- Frame export, final ranking, statistics