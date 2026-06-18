# Voronoi Generator

A terminal-based Voronoi diagram generator that produces beautiful, colorful tessellations using Unicode block characters and ANSI 256-color mode. A Voronoi diagram partitions a plane into regions based on distance to a set of "seed" points — each region contains all points closer to its seed than to any other.

![Python 3](https://img.shields.io/badge/python-3.7+-blue.svg)

## Features

- **5 distance metrics**: Euclidean, Manhattan, Chebyshev, Minkowski (p=3), and Cosine — each produces dramatically different cell shapes
- **5 seed placement patterns**: Random, Grid (jittered), Circular, Fibonacci Spiral, and Clustered — each creates unique compositions
- **6 color palettes**: Rainbow, Pastel, Neon, Earth, Ocean, and Fire
- **2 rendering modes**: Filled (solid colors) and Outline (borders only on dark background)
- **Border highlighting**: Optionally highlight cell boundaries with bright edges
- **Seed markers**: Show where seed points are located
- **Real-time animation**: Watch seeds bounce and Voronoi cells morph in real time
- **Double vertical resolution**: Uses Unicode half-block characters (▀) for sub-pixel rendering — each terminal row represents 2 pixel rows
- **Reproducible output**: Seed the RNG for deterministic results
- **Input validation**: Rejects invalid inputs (zero/negative seeds, invalid dimensions) with clear error messages
- **Robust edge handling**: Gracefully handles degenerate cases like cosine distance at the origin and empty grids
- **Zero dependencies**: Pure Python 3 standard library — no pip installs needed

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
                           clusters (default: random)
  -p, --palette PALETTE   Color palette: rainbow, pastel, neon, earth,
                           ocean, fire (default: rainbow)
  -m, --mode MODE         Rendering mode: filled, outline (default: filled)
  -b, --borders           Highlight cell borders with bright edges
  --seeds-visible          Show seed point markers
  -a, --animate           Animate seeds moving in real time
  --delay DELAY           Animation frame delay in seconds, must be > 0 (default: 0.08)
  --seed SEED             Random seed for reproducibility
  --version               Show version and exit
```

### Examples

```bash
# Neon palette with Manhattan distance — creates diamond-shaped cells
python3 voronoi.py --seeds 20 --palette neon --distance manhattan

# Fibonacci spiral seed pattern with ocean palette
python3 voronoi.py --seeds 50 --seed-type spiral --palette ocean

# Outline mode shows only cell boundaries, like a stained glass window
python3 voronoi.py --seeds 30 --mode outline --palette fire

# Chebyshev distance creates square-shaped cells
python3 voronoi.py --seeds 12 --distance chebyshev --palette pastel --borders

# Animate seeds bouncing around with real-time Voronoi updates
python3 voronoi.py --seeds 15 --animate --palette neon --delay 0.1

# Reproducible output with a fixed random seed
python3 voronoi.py --seeds 25 --seed 42 --palette earth --seed-type circular

# Clustered seeds create organic cell groupings
python3 voronoi.py --seeds 40 --seed-type clusters --palette fire --borders

# Cosine distance creates angular wedge cells from the origin
python3 voronoi.py --seeds 20 --distance cosine --palette rainbow

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

## Testing

Run the built-in test suite:

```bash
python3 test_voronoi.py
```

This runs 116 tests covering:
- All seed generators (random, grid, circular, spiral, clusters) with edge cases
- All palette generators with boundary values
- All 5 distance metrics including symmetry and edge cases
- Cosine distance degenerate cases (origin, identical points, opposite directions)
- Voronoi computation (empty seeds, single seed, small grids)
- Rendering (filled, outline, with/without borders, with/without dist_grid)
- CLI input validation (zero/negative seeds, invalid delays)
- All CLI flag combinations (every distance, palette, seed type, mode)
- Color math (HSV conversion, RGB-to-ANSI mapping)
- Seed marker filtering

## Changelog

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