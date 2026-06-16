# ASCII Topography Map Generator

Generate beautiful, detailed topographic maps in your terminal using Perlin noise. Features contour lines, rivers, lakes, named peaks, terrain shading with ANSI colors, elevation profiles, coordinate grid overlay, compass rose, terrain statistics, and interactive zoom/pan mode.

## Features

### Terrain Generation
- **Procedural terrain** using multi-octave Perlin noise with an island mask for natural coastlines
- **9 terrain types**: deep water, shallow water, beach, plains, forest, highland, mountain, peak, and snow — each with a distinct ASCII character and color
- **Contour lines**: automatically drawn at configurable elevation intervals (default: 5%)
- **Rivers**: traced downhill from high-elevation sources to the sea with adaptive source count based on map size
- **Lakes**: enclosed water basins not connected to the ocean are detected and displayed as distinct inland lakes (◊)
- **Named peaks**: local maxima are detected and labeled with procedurally generated names (e.g. "Mt. Eagle", "Pico Storm") and elevation in meters
- **Peak name pool**: expanded to 12 prefixes and 35 suffixes for more variety

### Visualization
- **ANSI 256-color support**: rich color output for supported terminals; monochrome fallback available
- **Compass rose**: decorative directional indicator (N/S/E/W) rendered below the map
- **Coordinate grid overlay**: toggle a grid of ┼/│/─ characters to help locate positions
- **Terrain statistics**: automatic breakdown of terrain composition (e.g. "forest 14%, mountain 20%")
- **Area stats**: map dimensions, elevation range, average elevation, water/land percentage

### Elevation Profiles
- **Row profiles**: `--profile row N` renders a vertical bar-chart elevation cross-section along any row
- **Column profiles**: `--profile col N` renders a profile along any column
- Profiles use terrain-colored blocks for visual clarity

### Interactive Mode
- **Zoom in/out** (+/-), **pan** (WASD), **regenerate** (r), **toggle grid** (g), and **quit** (q) — all in real-time
- Auto-sized to fit your terminal

### CLI
- **`--version`** flag to print version (v1.1.0)
- **`--help`** flag with examples and usage info
- **`--output FILE`** saves map to a file (ANSI codes stripped automatically)
- Deterministic seeding: same seed produces the same map every time
- Fully configurable: width, height, scale, octaves, contour interval, and more
- Input validation with clear error messages

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

# Print version
python3 topography.py --version
```

### Elevation Profiles

```bash
# Profile across row 15
python3 topography.py --profile row 15

# Profile down column 40
python3 topography.py --profile col 40

# Combine with seed for reproducibility
python3 topography.py --seed 42 --profile row 7
```

### Save to File

```bash
# Save map as plain text (ANSI codes stripped)
python3 topography.py --seed 42 --output my_map.txt
```

### Coordinate Grid

```bash
# Show grid overlay to help locate features
python3 topography.py --grid
```

### Interactive Mode

```bash
python3 topography.py --interactive
# or
python3 topography.py -i
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
| `G` | Toggle coordinate grid |
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

# Hide compass rose
python3 topography.py --no-compass

# Hide terrain statistics
python3 topography.py --no-stats

# Show raw elevation numbers (0-9) instead of terrain
python3 topography.py --elevation-numbers
```

## How It Works

1. **Perlin Noise**: A custom 2D Perlin noise implementation generates smooth random elevation values. Multiple octaves (layers at different frequencies) are combined for natural-looking terrain.

2. **Island Mask**: A radial distance-based mask lowers elevation near the edges, creating natural coastlines. A secondary noise layer warps the mask for irregular shorelines.

3. **Power Curve & Boost**: Elevation values are shaped with a power curve (`e^0.8`) to enhance peaks and valleys, then boosted to fill the full elevation range.

4. **Contour Lines**: For each cell, the algorithm checks if any neighbor crosses a different contour level. If so, a contour character (`░`) is drawn.

5. **Rivers**: Starting from random high-elevation points, rivers trace the steepest downhill path until they reach water. The number of river sources scales with map size.

6. **Lakes**: A flood-fill BFS from the map edges identifies all ocean-connected water cells. Any water cell not reachable from the edge is classified as an inland lake (◊).

7. **Peak Detection**: Local maxima in a 5×5 neighborhood above a threshold are identified, filtered for minimum spacing (adaptive to map size), and labeled with procedurally generated names.

8. **Terrain Classification**: Elevation values are mapped to 9 terrain types, each with a distinct ASCII character and ANSI color.

9. **Elevation Profiles**: A row or column's elevation values are rendered as a vertical bar chart using Unicode block characters, color-coded by terrain type.

## Output Example

```
  Topographic Map — Seed 42
  ╔──────────────────────────────────────────────────────────────────────────────────╗
  ║≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈~~~~~~~~~~~~~~~░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░║
  ║≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈~~~~~~~~.....░░░░░░░░░░░░░░░░░░░░░░░░░..~~~≈≈≈≈≈≈≈≈≈≈≈≈≈≈║
  ║≈≈≈≈≈≈≈≈~~.░░░░░░░░░░░░░░░░░░░░░░░░░░▲░░░░░░░░░░░░░░░░░░░░░░░░..~~≈≈≈≈≈≈≈≈≈≈≈║
  ╚──────────────────────────────────────────────────────────────────────────────────╝

        N
        ▲
    NW ╱ ╲ NE
      ╱   ╲
  W ◄  ┼  ► E
      ╲   ╱
    SW ╲ ╱ SE
        ▼
        S

  Legend:
  ≈ deep water (0%+)  ~ shallow water (12%+)  . beach (18%+)
  , plains (22%+)  ; forest (35%+)  + highland (50%+)
  / mountain (60%+)  ^ peak (72%+)  # snow (85%+)
  ░ contour lines (every 5%)
  ▼ rivers  ◊ lakes  ▲ peaks

  Peaks:
    ▲ Mt. Raven — 3930m  (col 13, row 16)
    ▲ Pico Storm — 3487m  (col 69, row 16)

  Area: 80×30  |  Elev: 0m–3930m  |  Avg: 1650m  |  Water: 28%  |  Land: 72%
  Terrain: beach 5%, deep water 18%, forest 14%, highland 19%, mountain 18%, plains 13%
```

## Running Tests

```bash
python3 -m pytest test_topography.py -v
```

The test suite (52 tests) covers Perlin noise determinism and range, terrain classification, map generation, rendering (color/no-color/grid/compass/stats/profiles), input validation (dimensions, octaves, scale), output features (file save, version), and edge cases (small maps, extreme scales, custom contour intervals, all features hidden).

## All Options

| Flag | Default | Description |
|------|---------|-------------|
| `--version` | — | Print version and exit |
| `--seed` | random | Random seed for reproducible maps |
| `--width` | 80 | Map width in characters |
| `--height` | 30 | Map height in characters |
| `--scale` | 0.04 | Noise scale factor (lower = bigger features) |
| `--octaves` | 6 | Number of noise octaves (1–12) |
| `--no-color` | off | Disable ANSI colors |
| `--no-contours` | off | Hide contour lines |
| `--no-rivers` | off | Hide rivers |
| `--no-labels` | off | Hide peak labels |
| `--no-legend` | off | Hide legend |
| `--no-compass` | off | Hide compass rose |
| `--no-stats` | off | Hide terrain statistics |
| `--elevation-numbers` | off | Show raw elevation as 0-9 digits |
| `--grid` | off | Show coordinate grid overlay |
| `--profile DIR IDX` | off | Render elevation profile (row/col N) |
| `--output FILE` | off | Save output to file (no ANSI codes) |
| `--interactive` / `-i` | off | Interactive zoom/pan mode |

## License

MIT