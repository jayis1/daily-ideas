# Barchart Race v2.0 — Animated ASCII Bar Chart Race Visualizer

Watch values compete and rankings shift over time with smooth terminal-based animated bar chart races. Like those viral YouTube videos, but right in your terminal — and now with percentage mode, growth charts, side-by-side comparisons, sparklines, ticker mode, and animated HTML export.

## Features

### Core
- **Animated bar chart races** — smooth ASCII animation with ease-in-out interpolation between time periods
- **5 built-in datasets** — tech company revenue, Olympic medals, programming language popularity, world population, cryptocurrency market cap
- **Random race generator** — generate unpredictable races with `--random` (use `--seed` for reproducibility)
- **Custom data** — load your own CSV or JSON files
- **Smart ranking** — bars reorder as values cross; medals (🥇🥈🥉) for top 3
- **Consistent series colors** — each series keeps its color across all frames (not recolored by rank)
- **Export** — save frames as individual text files or as a single flipbook-style movie file

### New in v2.0
- **Percentage mode** (`--percent`) — view values as share-of-total percentages, perfect for market share analysis
- **Growth mode** (`--growth`) — show percentage growth from the first period instead of absolute values
- **Side-by-side comparison** (`--compare`) — compare any two time periods with change indicators (↑↓) and percentage diffs
- **Compact ticker** (`--ticker`) — single-line scrolling summary for embedding in status bars or piped output
- **Animated HTML export** (`--html`) — generate a self-contained HTML file with CSS-animated bars and play/pause controls
- **Sparklines in stats** — the `--stats` view now shows unicode sparkline trends (▁▂▃▄▅▆▇█) per series and a growth ranking
- **Version flag** — `--version` now prints `2.0.0`

## Installation

No dependencies required — pure Python 3.6+:

```bash
# Just download and run
git clone <repo-url>
cd barchart-race
python3 barchart_race.py
```

## Usage

### Run the default demo (tech company revenue):
```bash
python3 barchart_race.py
```

### Choose a built-in dataset:
```bash
python3 barchart_race.py --sample tech-revenue
python3 barchart_race.py --sample olympic-medals
python3 barchart_race.py --sample programming-languages
python3 barchart_race.py --sample world-population
python3 barchart_race.py --sample crypto-marketcap
```

### List available datasets:
```bash
python3 barchart_race.py --list
```

### Generate a random race:
```bash
python3 barchart_race.py --random
python3 barchart_race.py --random --seed 42       # reproducible
```

### Load custom data:
```bash
python3 barchart_race.py --data my_data.csv
python3 barchart_race.py --data my_data.json
```

### Control the display:
```bash
python3 barchart_race.py --top 5          # show only top 5 bars
python3 barchart_race.py --speed 4         # faster animation (frames/sec)
python3 barchart_race.py --speed 0.5       # slower animation
python3 barchart_race.py --no-loop         # play once and stop
python3 barchart_race.py --no-color        # disable ANSI colors
python3 barchart_race.py --minimal          # compact display mode
```

### Percentage mode (market share):
```bash
python3 barchart_race.py --percent                  # share of total
python3 barchart_race.py --percent --sample crypto-marketcap
python3 barchart_race.py --percent --solve --top 5   # final share ranking
```

### Growth mode (change from start):
```bash
python3 barchart_race.py --growth                    # % growth from period 1
python3 barchart_race.py --growth --sample programming-languages
python3 barchart_race.py --growth --solve             # final growth ranking
```

### Side-by-side comparison:
```bash
python3 barchart_race.py --compare 0 -1              # first vs last period
python3 barchart_race.py --compare 0 5 --top 5        # period 0 vs 5, top 5
python3 barchart_race.py --compare 0 -1 --sample tech-revenue
```

### Compact ticker mode:
```bash
python3 barchart_race.py --ticker                     # scrolling one-line summary
python3 barchart_race.py --ticker --top 3              # top 3 only
```

### View final ranking (no animation):
```bash
python3 barchart_race.py --solve
python3 barchart_race.py --solve --sample olympic-medals --top 5
python3 barchart_race.py --solve --percent --sample crypto-marketcap
```

### View statistics with sparklines:
```bash
python3 barchart_race.py --stats --sample programming-languages
python3 barchart_race.py --stats --growth --sample tech-revenue
```

### Export as animated HTML:
```bash
python3 barchart_race.py --html output.html
python3 barchart_race.py --html output.html --speed 1 --top 10
```

### Export frames:
```bash
python3 barchart_race.py --export frames/              # individual text files
python3 barchart_race.py --export-movie movie.txt       # single file with form feeds
```

## Data Format

### CSV Format
```csv
label,Company A,Company B,Company C
Jan,10,20,15
Feb,12,18,17
Mar,15,22,20
```

### JSON Format
```json
{
  "title": "My Chart Race",
  "unit": "$",
  "data": {
    "Company A": [10, 12, 15],
    "Company B": [20, 18, 22],
    "Company C": [15, 17, 20]
  },
  "labels": ["Jan", "Feb", "Mar"]
}
```

## Example Output

### Final Ranking (`--solve`)
```
=== Final Ranking: Tech Company Revenue ($B) ===

 🥇  1. Apple  ██████████████████████████████ 150.0$B
 🥈  2. Amazon  ████████████████████████ 120.0$B
 🥉  3. NVIDIA  ████████████████████████ 120.0$B
     4. Microsoft  ███████████████████████ 115.0$B
     5. Google  ████████████████████ 103.0$B

 Biggest gainer: NVIDIA (112.0$B change)
 Biggest loser:  Intel (6.0$B change)

 Rank changes:
   NVIDIA: ↑6 (#9 → #3)
   Samsung: ↓5 (#2 → #7)
   Tesla: ↑4 (#10 → #6)
```

### Statistics with Sparklines (`--stats`)
```
=== Statistics: Programming Language Popularity (TIOBE Index) ===

  Series count:    10
  Time periods:    14

  Series               Min      Max     Mean   Growth        Trend
  ─────────────── ──────── ──────── ──────── ──────── ────────────
  Python               5.0     30.0     15.9    +25.0 ▁▁▁▁▂▂▃▄▄▅▆▆
  C                    9.0     16.0     12.4     -7.0 █▇▆▅▄▄▄▄▅▅▄▃
  Java                 7.0     20.0     13.5    -13.0 █▇▆▆▅▅▄▄▃▃▂▂
  ...

  Growth Ranking:
    🥇 Python: 25.0% (+500.0%)
    🥈 Rust: 6.0%
    🥉 TypeScript: 5.0%
```

### Comparison (`--compare 0 -1`)
```
=== Tech Company Revenue ($B) ===
  Comparing: Q1'21 vs Q2'24

 🥇 Apple           ████████ → ████████████████████  ↑+85.0$B
 🥈 Amazon          ████ → ████████████████  ↑+85.0$B
 🥉 NVIDIA          █ → ████████████████  ↑+112.0$B

  Series                From         To     Change        %
  ─────────────── ────────── ────────── ────────── ────────
  NVIDIA               8.0$B    120.0$B    112.0$B +1400.0%
  Amazon              35.0$B    120.0$B     85.0$B  +242.9%
  Apple               65.0$B    150.0$B     85.0$B  +130.8%
```

## How It Works

- **Interpolation**: For each pair of consecutive data points, intermediate frames are generated using an ease-in-out curve (`3t² - 2t³`), creating natural-looking transitions.
- **Rendering**: Bars are drawn with Unicode block characters and ANSI color codes, with ranking recalculated at every frame.
- **Series coloring**: Each series gets a consistent color based on its position in the dataset, so you can track the same entity across all frames.
- **Percentage mode**: Values are normalized to 100% of the total for each period, ideal for market share visualization.
- **Growth mode**: Values are shown as percentage change from the first period (absolute change used when starting value is 0).
- **HTML export**: Generates a self-contained HTML file with CSS transitions for smooth bar animations and JavaScript controls for play/pause/frame-stepping.

## Running Tests

```bash
python3 test_barchart_race.py
```

39 tests covering data validation, interpolation, rendering, CSV/JSON loading, export, statistics, sparklines, percentage/growth transforms, comparisons, ticker mode, HTML export, edge cases, and more.