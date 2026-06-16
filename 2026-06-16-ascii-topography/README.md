# ASCII Topography Map Generator

Generate beautiful, detailed topographic maps in your terminal using Perlin noise. Features contour lines, rivers, named peaks, terrain shading with ANSI colors, and interactive zoom/pan mode.

![topography screenshot](https://i.imgur.com/placeholder.png)

## Features

- **Procedural terrain generation** using multi-octave Perlin noise with an island mask for natural coastlines
- **9 terrain types**: deep water, shallow water, beach, plains, forest, highland, mountain, peak, and snow — each with a distinct ASCII character and color
- **Contour lines**: automatically drawn at configurable elevation intervals (default: 5%)
- **Rivers**: traced downhill from high-elevation sources to the sea
- **Named peaks**: local maxima are detected and labeled with procedurally generated names (e.g. "Mt. Eagle", "Pico Storm") and elevation in meters
- **ANSI 256-color support**: rich color output for supported terminals; monochrome fallback available
- **Interactive mode**: zoom in/out (+/-), pan (WASD), regenerate (r), and quit (q) — all in real-time
- **Deterministic seeding**: same seed produces the same map every time
- **Fully configurable**: width, height, scale, octaves, contour interval, and more

## Installation

No dependencies required — uses only Python standard library:

```bash
# Just download and run
python3 topography.py

# Or clone the repo
git clone https://github.com/your-username/daily-ideas.git
cd daily-ideas/2026-06-16-ascii-topography
python3 topography.py
```

Requires Python 3.7+ (uses f-strings and `math` module only).

## Usage

### Basic

```bash
# Generate a random map (80x30, with colors)
python3 topography.py

# Generate with a specific seed for reproducibility
python3 topography.py --seed 1337

# Custom dimensions
python3 topography.py --width 100 --height 40

# Monochrome output (no ANSI colors)
python3 topography.py --no-color

# Adjust noise scale (lower = more zoomed out, bigger features)
python3 topography.py --scale 0.02

# More octaves = more detail (but slower)
python3 topography.py --octaves 8
```

### Interactive Mode

```bash
python3 topography.py --interactive
```

Controls:
| Key | Action |
|-----|--------|
| `+` / `=` | Zoom in |
| `-` / `_` | Zoom out |
| `W` / `↑` | Pan up |
| `S` / `↓` | Pan down |
| `A` / `←` | Pan left |
| `D` / `→` | Pan right |
| `R` | Generate new random map |
| `Q` | Quit |

### Toggle Features

```bash
# Hide contour lines
python3 topography.py --no-contours

# Hide rivers
python3 topography.py --no-rivers

# Hide peak labels
python3 topography.py --no-labels

# Hide legend
python3 topography.py --no-legend

# Show raw elevation numbers (0-9) instead of terrain
python3 topography.py --elevation-numbers
```

## How It Works

1. **Perlin Noise**: A custom 2D Perlin noise implementation generates smooth random elevation values. Multiple octaves (layers at different frequencies) are combined for natural-looking terrain.

2. **Island Mask**: A radial distance-based mask lowers elevation near the edges, creating natural coastlines. A secondary noise layer warps the mask for irregular shorelines.

3. **Power Curve & Boost**: Elevation values are shaped with a power curve (`e^0.8`) to enhance peaks and valleys, then boosted to fill the full elevation range.

4. **Contour Lines**: For each cell, the algorithm checks if any neighbor crosses a different contour level. If so, a contour character (`░`) is drawn.

5. **Rivers**: Starting from random high-elevation points, rivers trace the steepest downhill path until they reach water. This creates natural-looking drainage patterns.

6. **Peak Detection**: Local maxima in a 5×5 neighborhood above a threshold are identified, filtered for minimum spacing, and labeled with procedurally generated names.

7. **Terrain Classification**: Elevation values are mapped to 9 terrain types, each with a distinct ASCII character and ANSI color.

## Output Example

```
  Topographic Map — Seed 1337
  ╔──────────────────────────────────────────────────────────────────────────────────╗
  ║≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈~~~~~~~~~~~~~~~≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈║
  ║≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈~~~~~~~~.....░░░░░░░░░░░░░░░░░░░░░░░░░..~~~≈≈≈≈≈≈≈≈≈≈≈≈≈≈║
  ║≈≈≈≈≈≈≈≈~~.░░░░░░░░░░░░░░░░░░░░░░░░░░▲░░░░░░░░░░░░░░░░░░░░░░░░..~~≈≈≈≈≈≈≈≈≈≈≈║
  ║≈≈~~.░░░░░░░░░░░░░░░░░///░░░░░░░//^░/^////////░░/░░░░+░░░░░░░░░░░░░░░░░░░░.~~║
  ║~.░░░░░░░░░░░░░^░░░/░░░░░░░░░░/░░░░░░░░░░░░░░░░/░░+░░░░░░░░░░░░░░░░░░░░░░░░░.~║
  ╚──────────────────────────────────────────────────────────────────────────────────╝

  Peaks:
    ▲ Tor Bear — 3930m  (col 13, row 16)
    ▲ Mt. Hawk — 3487m  (col 69, row 16)

  Legend:
  ≈ deep water (0%+)  ~ shallow water (12%+)  . beach (18%+)
  , plains (22%+)  ; forest (35%+)  + highland (50%+)
  / mountain (60%+)  ^ peak (72%+)  # snow (85%+)
  ░ contour lines (every 5%)
  ▼ rivers  ▲ peaks
```

## All Options

| Flag | Default | Description |
|------|---------|-------------|
| `--seed` | random | Random seed for reproducible maps |
| `--width` | 80 | Map width in characters |
| `--height` | 30 | Map height in characters |
| `--scale` | 0.04 | Noise scale factor (lower = bigger features) |
| `--octaves` | 6 | Number of noise octaves |
| `--no-color` | off | Disable ANSI colors |
| `--no-contours` | off | Hide contour lines |
| `--no-rivers` | off | Hide rivers |
| `--no-labels` | off | Hide peak labels |
| `--no-legend` | off | Hide legend |
| `--elevation-numbers` | off | Show raw elevation as 0-9 digits |
| `--interactive` / `-i` | off | Interactive zoom/pan mode |

## License

MIT