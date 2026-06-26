# Terminal Spirograph

A command-line tool that generates stunning mathematical curve patterns directly in your terminal using ASCII/Unicode density characters. Supports four curve families — hypotrochoids, epitrochoids, rose curves, and Lissajous figures — with animated drawing, color palettes, SVG export, named presets, continuous loop mode, and seeded random generation.

## Features

- **4 curve types**: Hypotrochoid, Epitrochoid, Rose, and Lissajous curves
- **Animated drawing**: Watch the spirograph being drawn progressively with a progress indicator
- **Color palettes**: Auto, rainbow, gradient, or monochrome rendering with ANSI colors
- **Random generation**: Generate random aesthetically-pleasing parameters with `--random`
- **Seeded randomness**: Reproduce any random curve with `--seed` for shareable results
- **Named presets**: 13 built-in presets like `classic`, `starflower`, `infinity` — run `--list-presets`
- **Gallery mode**: Showcase all four curve types in sequence with `--gallery`
- **Loop mode**: Continuously generate random spirographs with `--loop` until Ctrl+C
- **SVG export**: Save curves as vector SVG files with `--export-svg` for high-quality printing
- **Density rendering**: Point density maps to Unicode characters (·:;+*#░▒▓█) for smooth visuals
- **Two character sets**: Block (bold, high contrast) and fine (detailed, nuanced)
- **`--version` and `--help`**: Full CLI documentation built in
- **Input validation**: Catches division-by-zero and invalid parameters before rendering
- **No dependencies**: Uses only the Python standard library

## How to Install

No dependencies required — uses only Python standard library modules:

```bash
# Just clone and run
git clone https://github.com/jayis1/daily-ideas.git
cd daily-ideas/2026-06-26-terminal-spirograph
chmod +x spirograph.py
```

Requires Python 3.6+ (uses `math`, `random`, `time`, `sys`, `argparse`, `collections`, `os`).

## How to Run

```bash
# Random animated spirograph (default)
python3 spirograph.py

# Specific hypotrochoid (the classic spirograph)
python3 spirograph.py --hypo --R 11 --r 4 --d 6

# Epitrochoid
python3 spirograph.py --epi --R 7 --r 3 --d 5

# Rose curve
python3 spirograph.py --rose --k 5 --n 3

# Lissajous figure
python3 spirograph.py --lissajous --a 3 --b 4 --delta 1.5708

# Random curve of any type
python3 spirograph.py --random

# Reproducible random (same seed = same curve every time)
python3 spirograph.py --random --seed 42

# Named preset
python3 spirograph.py --preset classic

# List all presets
python3 spirograph.py --list-presets

# Gallery mode — shows all four curve types
python3 spirograph.py --gallery

# Loop mode — continuous random spirographs
python3 spirograph.py --loop

# Export as SVG
python3 spirograph.py --preset starflower --export-svg output.svg

# Rainbow-colored rendering
python3 spirograph.py --hypo --random --palette rainbow

# Static render (no animation, good for piping)
python3 spirograph.py --hypo --R 21 --r 8 --d 5 --static

# Fine character set for more detail
python3 spirograph.py --lissajous --random --chars fine

# Custom size and animation speed
python3 spirograph.py --random --width 100 --height 40 --frames 60 --fps 20

# Version info
python3 spirograph.py --version

# Full help
python3 spirograph.py --help
```

## Usage Examples

### Classic Spirograph (Hypotrochoid)
The hypotrochoid is the classic spirograph pattern — a small circle rolling inside a larger one:
```
python3 spirograph.py --hypo --R 21 --r 8 --d 5
```

### Star-like Epitrochoid
Epitrochoids have the small circle rolling on the outside, creating star/flower shapes:
```
python3 spirograph.py --epi --R 9 --r 4 --d 7
```

### Rose Curve
Rose curves create petal-like patterns based on polar equations:
```
python3 spirograph.py --rose --k 7 --n 4
```

### Lissajous Figure
Lissajous curves create elegant looping patterns from two perpendicular oscillations:
```
python3 spirograph.py --lissajous --a 5 --b 6 --delta 1.5708
```

### Seeded Reproducibility
Share exact curves with others using the `--seed` flag:
```
python3 spirograph.py --random --seed 42
```

### SVG Export
Save high-quality vector output for embedding in documents or printing:
```
python3 spirograph.py --preset infinity --export-svg infinity.svg
```

## Built-in Presets

| Preset | Curve Type | Parameters |
|--------|-----------|------------|
| classic | Hypotrochoid | R=11, r=4, d=6 |
| starflower | Hypotrochoid | R=21, r=8, d=5 |
| daisy | Hypotrochoid | R=15, r=7, d=9 |
| vortex | Hypotrochoid | R=19, r=6, d=8 |
| sunburst | Epitrochoid | R=9, r=4, d=7 |
| pinwheel | Epitrochoid | R=7, r=3, d=5 |
| lotus | Epitrochoid | R=11, r=5, d=8 |
| pentarose | Rose | k=5, n=3, d=10 |
| heptarose | Rose | k=7, n=4, d=10 |
| trefoil | Rose | k=3, n=1, d=10 |
| bowtie | Lissajous | a=3, b=2, δ=π/4 |
| infinity | Lissajous | a=3, b=4, δ=π/2 |
| butterfly | Lissajous | a=5, b=6, δ=π/2 |

## What It Does

Terminal Spirograph computes mathematical spirograph curves by evaluating parametric equations at thousands of points, then maps those points onto a character grid. The density of overlapping points at each grid position determines which Unicode character is used — from spaces (empty) through `·:;+*#░▒▓█` (most dense).

**Curve mathematics:**
- **Hypotrochoid**: `(R-r)cos(t) + d·cos((R-r)t/r), (R-r)sin(t) - d·sin((R-r)t/r)` — circle rolling inside a circle
- **Epitrochoid**: `(R+r)cos(t) - d·cos((R+r)t/r), (R+r)sin(t) - d·sin((R+r)t/r)` — circle rolling outside a circle
- **Rose**: `d·cos(k/n·t)·cos(t), d·cos(k/n·t)·sin(t)` — polar rose in Cartesian form
- **Lissajous**: `d·sin(at+δ), d·sin(bt)` — parametric oscillation curves

The animation progressively reveals the curve by drawing more points each frame, creating a satisfying "watch it spin" experience reminiscent of a real spirograph pen.

## Running Tests

```bash
cd 2026-06-26-terminal-spirograph
python3 -m pytest test_spirograph.py -v
```

44 tests covering parametric math, rendering, colorization, parameter generation, presets, SVG export, and full pipeline integration.