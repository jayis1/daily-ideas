# ✦ ASCII Kaleidoscope

A mesmerizing terminal-based kaleidoscope that generates real-time, animated, symmetric patterns using Unicode block characters and ANSI 256-color mode. The engine computes patterns in a single triangular wedge and mirrors them across multiple axes of symmetry — just like a real kaleidoscope!

![kaleidoscope](https://img.shields.io/badge/type-visualization-purple) ![python](https://img.shields.io/badge/python-3.7+-blue) ![terminal](https://img.shields.io/badge/output-ANSI%20256-green)

## Features

- **6 unique pattern modes**: spiral, ripple, crystal, flower, mandala, wave
- **Configurable symmetry**: 4 to 16+ segments of kaleidoscopic mirroring
- **Smooth animation**: Half-block Unicode characters (▀/▄) give each terminal row 2 virtual pixels for higher visual fidelity
- **ANSI 256-color palette**: Dynamically shifting hues create ever-evolving color cycles
- **Interactive controls**:
  - `r` — switch to a random new pattern
  - `space` — pause/resume animation
  - `+` / `-` — speed up or slow down
  - `q` — quit
- **Randomized parameters**: Each run seeds frequencies and phases differently, so every session produces unique patterns
- **Zero dependencies**: Pure Python standard library — no installs needed

## How It Works

1. Each frame, the viewport is treated as a circular region in polar coordinates.
2. The angle `θ` is folded into a single "wedge" segment (e.g., for 8-fold symmetry, each wedge spans 45°).
3. Every other wedge is mirror-reflected, creating perfect kaleidoscopic symmetry.
4. The pattern function combines multiple sinusoidal waves in `r` and `θ` with time-varying phases.
5. Upper/lower half-block characters (▀/▄) encode two vertical sub-pixels per terminal row, with foreground and background colors set independently for sub-pixel color depth.
6. The color palette slowly shifts over time, producing hypnotic hue cycling.

## Installation

No installation required — just Python 3.7+:

```bash
# Clone or download, then:
cd 2026-06-14-ascii-kaleidoscope
```

## How to Run

```bash
# Default: random pattern, 8 segments
python3 kaleidoscope.py

# Choose a specific pattern
python3 kaleidoscope.py --pattern spiral
python3 kaleidoscope.py --pattern crystal
python3 kaleidoscope.py --pattern flower

# More segments = more mirrors
python3 kaleidoscope.py --segments 12

# Slow it down or speed it up
python3 kaleidoscope.py --speed 0.5
python3 kaleidoscope.py --speed 3.0

# Combine options
python3 kaleidoscope.py -p mandala -s 16 --speed 1.5
```

### Available Patterns

| Pattern   | Description                                        |
|-----------|----------------------------------------------------|
| `spiral`  | Classic swirling spirals with multi-frequency arms  |
| `ripple`  | Concentric wave ripples radiating outward           |
| `crystal` | Geometric crystal-like facets and shards            |
| `flower`  | Organic petal-like forms that bloom and shift       |
| `mandala` | Sacred-geometry style with rings and spokes         |
| `wave`    | Ocean-inspired wave interference patterns            |

## Usage Examples

```bash
# Quick meditative moment
python3 kaleidoscope.py -p mandala --speed 0.5

# High-energy visual
python3 kaleidoscope.py -p crystal -s 12 --speed 3.0

# Simple and soothing
python3 kaleidoscope.py -p ripple --segments 6

# Full-screen kaleidoscope (maximize your terminal first!)
python3 kaleidoscope.py
```

While running, press:
- **r** — randomize to a different pattern
- **space** — pause/resume
- **+** — increase speed
- **-** — decrease speed
- **q** or **Ctrl+C** — quit

## Testing

```bash
python3 test_kaleidoscope.py
```

Runs unit tests verifying all 6 patterns render correctly, different segment counts work, and sequential animation frames are produced.

## What It Does

The ASCII Kaleidoscope transforms your terminal into a mesmerizing light show. It mathematically generates wave interference patterns in polar coordinates, folds them through kaleidoscopic symmetry, and renders the result as a smoothly animated, color-cycling display. Each session is unique thanks to randomized frequency and phase parameters. It's both a visual toy and a demonstration of how simple trigonometric functions, when composed and reflected through symmetry, can produce stunningly complex and beautiful results.