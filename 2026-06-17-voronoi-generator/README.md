# Voronoi Generator v2.0.0

A terminal-based Voronoi diagram generator that produces beautiful, colorful tessellations using Unicode block characters and ANSI 256-color mode. A Voronoi diagram partitions a plane into regions based on distance to a set of "seed" points — each region contains all points closer to its seed than to any other.

![Python 3](https://img.shields.io/badge/python-3.7+-blue.svg)

## Features

### Distance Metrics (6)
- **Euclidean** — Classic straight-line distance → convex cells
- **Manhattan** — Grid/city-block distance → diamond-shaped cells
- **Chebyshev** — Chessboard distance → square cells aligned with axes
- **Minkowski (p=3)** — Generalized distance → rounded square cells
- **Cosine** — Angle-based distance → angular wedge cells from origin

### Seed Placement Patterns (6)
- **Random** — Uniform random placement
- **Grid** — Approximate grid with jitter for even spacing
- **Circular** — Concentric rings of seeds
- **Spiral** — Fibonacci/golden angle spiral
- **Clusters** — Grouped around random cluster centers
- **Hexagonal** — Hexagonal lattice placement for optimal packing *(new in v2.0)*

### Color Palettes (7)
- **Rainbow** — Full hue spectrum
- **Pastel** — Soft, muted tones
- **Neon** — Bright vivid colors on dark backgrounds
- **Earth** — Natural browns, greens, blues
- **Ocean** — Blues and greens
- **Fire** — Reds, oranges, yellows
- **Aurora** — Northern lights greens, teals, purples, and pinks *(new in v2.0)*

### Rendering Modes (3)
- **Filled** — Solid color cells (default)
- **Outline** — Only cell borders on dark background, like stained glass
- **Gradient** — Distance-based shading creates 3D-like depth effect within cells *(new in v2.0)*

### Other Features
- **Border highlighting** — Optionally highlight cell boundaries with bright white edges
- **Seed markers** — Show where seed points are located
- **Real-time animation** — Watch seeds bounce and Voronoi cells morph in real time
- **SVG export** — Save diagrams as scalable vector graphics files with `--export` *(new in v2.0)*
- **Diagram statistics** — Display cell sizes, distribution bars, and extreme values with `--info` *(new in v2.0)*
- **Double vertical resolution** — Uses Unicode half-block characters (▀) for sub-pixel rendering
- **Reproducible output** — Seed the RNG for deterministic results
- **Input validation** — Rejects invalid inputs with clear error messages
- **Zero dependencies** — Pure Python 3 standard library — no pip installs needed

## How It Works

A Voronoi diagram is one of the simplest and most elegant constructs in computational geometry. Given a set of **seed points**, the diagram assigns every pixel on the screen to the nearest seed. The result is a partition of the plane into convex cells, where each cell contains all points closer to its seed than to any other.

The tool computes this by brute force — for every pixel position, it checks the distance to all seeds and assigns it to the nearest one. The distance function determines the "shape" of the cells:

| Metric | Cell Shape |
|---|---|
| Euclidean | Classic convex cells |
| Manhattan | Diamond/rhombus-shaped cells |
| Chebyshev | Square cells (aligned with axes) |
| Minkowski p=3 | Rounded squares |
| Cosine | Angular wedge cells from origin |

For rendering, each terminal character cell represents two vertical pixels using the upper-half-block character (▀) — the foreground color maps to the upper pixel and the background color to the lower pixel, effectively doubling vertical resolution.

## Installation

No installation needed beyond Python 3.7+:

```bash
# Just run it directly
python3 voronoi.py
```

Or make it executable:

```bash
chmod +x voronoi.py
./voronoi.py
```

## Usage

### Basic Usage

```bash
# Default: 15 random seeds, rainbow palette, euclidean distance
python3 voronoi.py
```

### All Options

```
python3 voronoi.py [OPTIONS]

Options:
  -n, --seeds SEEDS       Number of seed points, must be ≥ 1 (default: 15)
  -w, --width WIDTH       Terminal width in columns (default: auto-detect)
  -H, --height HEIGHT     Pixel height (default: 2x terminal rows)
  -d, --distance METRIC   Distance metric: euclidean, manhattan, chebyshev,
                           minkowski3, cosine (default: euclidean)
  -s, --seed-type TYPE    Seed pattern: random, grid, circular, spiral,
                           clusters, hexagonal (default: random)
  -p, --palette PALETTE   Color palette: rainbow, pastel, neon, earth,
                           ocean, fire, aurora (default: rainbow)
  -m, --mode MODE         Rendering mode: filled, outline, gradient
                           (default: filled)
  -b, --borders           Highlight cell borders with bright edges
  --seeds-visible          Show seed point markers
  -i, --info              Show diagram statistics (cell sizes, distribution)
  -a, --animate            Animate seeds moving in real time
  --delay DELAY           Animation frame delay in seconds, must be > 0
                           (default: 0.08)
  --seed SEED             Random seed for reproducibility
  --export FILE.svg       Export the diagram as an SVG file
  --version               Show version and exit
  --help                  Show help message and exit
```

### Examples

```bash
# Neon palette with Manhattan distance — creates diamond-shaped cells
python3 voronoi.py --seeds 20 --palette neon --distance manhattan

# Fibonacci spiral seed pattern with ocean palette
python3 voronoi.py --seeds 50 --seed-type spiral --palette ocean

# Outline mode shows only cell boundaries, like a stained glass window
python3 voronoi.py --seeds 30 --mode outline --palette fire

# Gradient mode creates a 3D depth effect — cells shade from bright to dark
python3 voronoi.py --seeds 15 --mode gradient --palette aurora --borders

# Hexagonal seed pattern with aurora palette for an organic look
python3 voronoi.py --seeds 40 --seed-type hexagonal --palette aurora

# Chebyshev distance creates square-shaped cells
python3 voronoi.py --seeds 12 --distance chebyshev --palette pastel --borders

# Show diagram statistics — cell sizes and distribution
python3 voronoi.py --seeds 20 --info --palette earth

# Animate seeds bouncing around with real-time Voronoi updates
python3 voronoi.py --seeds 15 --animate --palette neon --delay 0.1

# Export as SVG for sharing or printing
python3 voronoi.py --seeds 25 --palette fire --export voronoi.svg

# Reproducible output with a fixed random seed
python3 voronoi.py --seeds 25 --seed 42 --palette earth --seed-type circular

# All new features combined: gradient + aurora + hexagonal + borders + info + export
python3 voronoi.py --seeds 30 --seed-type hexagonal --palette aurora \
  --mode gradient --borders --info --export output.svg

# Check version
python3 voronoi.py --version
```

## Input Validation

The tool validates all inputs and provides clear error messages:

```bash
$ python3 voronoi.py --seeds 0
error: Number of seeds must be at least 1, got 0

$ python3 voronoi.py --seeds -5
error: Number of seeds must be at least 1, got -5

$ python3 voronoi.py --delay -0.1 --seeds 5
error: Frame delay must be positive, got -0.1
```

## What's New in v2.0

- **Gradient rendering mode** (`--mode gradient`) — Distance-based shading creates a 3D depth effect within each cell, with seeds appearing bright and cell edges appearing darker
- **Aurora color palette** (`--palette aurora`) — Northern lights inspired greens, teals, purples, and pinks with shimmer variation
- **Hexagonal seed pattern** (`--seed-type hexagonal`) — Evenly-spaced triangular lattice placement for optimal cell distribution
- **SVG export** (`--export diagram.svg`) — Save the Voronoi diagram as a proper SVG file with colored cells, seed markers, and metadata
- **Diagram statistics** (`--info`) — Display cell size statistics, largest/smallest cells, and a text-based distribution bar chart
- **Color utility functions** — `_darken_color()`, `_lighten_color()`, `_ansi_to_rgb()` for gradient rendering and SVG export
- **62 new tests** — Expanded from 116 to 178 tests covering all new features

## Testing

Run the built-in test suite:

```bash
python3 test_voronoi.py
```

This runs 178 tests covering:
- All seed generators (random, grid, circular, spiral, clusters, hexagonal) with edge cases
- All palette generators (rainbow, pastel, neon, earth, ocean, fire, aurora) with boundary values
- All 5 distance metrics including symmetry and edge cases
- Cosine distance degenerate cases (origin, identical points, opposite directions)
- Voronoi computation (empty seeds, single seed, small grids)
- Voronoi info/statistics function
- Gradient rendering mode
- Color utilities (ANSI-to-RGB, darken, lighten, round-trip)
- SVG export (content validation, empty grid handling)
- Rendering (filled, outline, gradient, with/without borders)
- CLI input validation (zero/negative seeds, invalid delays)
- All CLI flag combinations (every distance, palette, seed type, mode)
- CLI info and export flags
- Color math (HSV conversion, RGB-to-ANSI mapping)
- Seed marker filtering

## Changelog

### v2.0.0 — New Features
- **Added: Gradient rendering mode** — `--mode gradient` creates distance-based shading for a 3D depth effect
- **Added: Aurora color palette** — `--palette aurora` with northern lights inspired colors
- **Added: Hexagonal seed pattern** — `--seed-type hexagonal` for optimal hex lattice placement
- **Added: SVG export** — `--export FILE.svg` saves the diagram as a vector graphic
- **Added: Diagram statistics** — `--info` displays cell sizes, largest/smallest cells, and distribution
- **Added: Color utility functions** — `_darken_color()`, `_lighten_color()`, `_ansi_to_rgb()` for gradient rendering and SVG export
- **Updated: Test suite** — Expanded from 116 to 178 tests covering all new features

### v1.1.0 — Bug Fixes
- **Fixed: ZeroDivisionError crash with `--seeds 0`** — Empty colors list caused `idx % len(colors)` division by zero in `render_block`. Now validates seeds ≥ 1 and handles empty grids gracefully.
- **Fixed: Crash with negative seed count** — `--seeds -1` was accepted and caused crashes. Now rejected with a clear error message.
- **Fixed: Empty seeds produced invalid grid** — `compute_voronoi([], w, h)` created a grid where every cell referenced non-existent seed index 0. Now returns an empty list for empty seeds.
- **Fixed: Zero-dimension grids not handled** — `compute_voronoi(seeds, 0, h)` returned a non-empty grid. Now returns an empty list for zero dimensions.
- **Fixed: Cosine distance degenerate at origin** — `dist_cosine(0,0, x,y)` returned 1.0 for all points because zero-magnitude vectors make cosine undefined. Now falls back to Euclidean distance for zero-magnitude vectors, and clamps cosine similarity to [-1, 1] to handle floating-point drift.
- **Fixed: No `--version` flag** — Added `--version` flag showing `voronoi 1.1.0`.
- **Fixed: No validation of `--delay`** — Negative or zero delay values were accepted. Now requires delay > 0.
- **Added: Input validation for dimensions** — Width and height < 1 are now rejected with clear error messages.
- **Added: Guard clauses in `render_block`** — Returns empty list when colors or grid are empty, preventing crashes.
- **Added: Guard clauses in `compute_voronoi_with_distance`** — Returns `([], [])` for empty seeds or zero dimensions.