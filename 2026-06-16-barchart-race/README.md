# Barchart Race — Animated ASCII Bar Chart Race Visualizer

Watch values compete and rankings shift over time with smooth terminal-based animated bar chart races. Like those viral YouTube videos, but right in your terminal.

## Features

- **Animated bar chart races** — smooth ASCII animation with easing interpolation between time periods
- **5 built-in datasets** — tech company revenue, Olympic medals, programming language popularity, world population, cryptocurrency market cap
- **Random race generator** — generate unpredictable races with `--random`
- **Custom data** — load your own CSV or JSON files
- **Smart ranking** — bars automatically reorder as values cross, medals for top 3
- **Statistics** — view min/max/mean/growth per series, rank changes, and cross-series correlations
- **Final ranking** — instant solve showing who won, biggest movers, and rank changes
- **Export** — save frames as individual text files or as a single flipbook-style movie file
- **Customizable** — control speed, top-N filtering, color, display mode, and looping

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
python3 barchart_race.py --speed 4        # faster animation (frames/sec)
python3 barchart_race.py --speed 0.5      # slower animation
python3 barchart_race.py --no-loop        # play once and stop
python3 barchart_race.py --no-color       # disable ANSI colors
python3 barchart_race.py --minimal        # compact display mode
```

### View final ranking (no animation):
```bash
python3 barchart_race.py --solve
python3 barchart_race.py --solve --sample olympic-medals --top 5
```

### View statistics:
```bash
python3 barchart_race.py --stats --sample programming-languages
```

### Export frames:
```bash
python3 barchart_race.py --export frames/           # individual text files
python3 barchart_race.py --export-movie movie.txt    # single file with form feeds
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

## How It Works

The tool uses a BFS-style interpolation between time periods to create smooth animations. For each pair of consecutive data points, it generates intermediate frames using an ease-in-out curve (`3t² - 2t³`), creating natural-looking transitions. Bars are rendered with Unicode block characters and ANSI color codes, with ranking recalculated at every frame.

## Running Tests

```bash
python3 test_barchart_race.py
```

23 tests covering data validation, interpolation, rendering, CSV/JSON loading, export, statistics, edge cases, and more.