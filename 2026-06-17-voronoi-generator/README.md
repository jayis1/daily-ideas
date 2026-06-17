# Voronoi Generator

A terminal-based Voronoi diagram generator that produces beautiful, colorful tessellations using Unicode block characters and ANSI 256-color mode. A Voronoi diagram partitions a plane into regions based on distance to a set of "seed" points — each region contains all points closer to its seed than to any other.

![Python 3](https://img.shields.io/badge/python-3.11+-blue.svg)

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

No installation needed beyond Python 3.11+:

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

```bash
python3 voronoi.py [OPTIONS]

Options:
  -n, --seeds SEEDS     Number of seed points (default: 15)
  -w, --width WIDTH     Terminal width in columns (default: auto-detect)
  -H, --height HEIGHT   Pixel height (default: 2x terminal rows)
  -d, --distance METRIC Distance metric: euclidean, manhattan, chebyshev,
                         minkowski3, cosine (default: euclidean)
  -s, --seed-type TYPE  Seed pattern: random, grid, circular, spiral,
                         clusters (default: random)
  -p, --palette PALETTE Color palette: rainbow, pastel, neon, earth,
                         ocean, fire (default: rainbow)
  -m, --mode MODE       Rendering mode: filled, outline (default: filled)
  -b, --borders         Highlight cell borders with bright edges
  --seeds-visible        Show seed point markers
  -a, --animate         Animate seeds moving in real time
  --delay DELAY         Animation frame delay in seconds (default: 0.08)
  --seed SEED           Random seed for reproducibility
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
```

## What It Does

1. **Generates seed points** using one of five placement strategies (random, grid+jitter, circular, spiral, clusters)
2. **Assigns colors** from the chosen palette to each seed
3. **Computes the Voronoi tessellation** using the selected distance metric — for every pixel, finds the closest seed
4. **Detects cell borders** by checking if adjacent pixels belong to different cells
5. **Renders to terminal** using ANSI 256-color codes and Unicode half-block characters for double vertical resolution
6. In **animation mode**, seeds bounce off walls with drift and damping, and the diagram is recomputed each frame

The result is a colorful, dynamically partitioned view of the terminal that looks like a stained glass window, a geographic territory map, or an abstract geometric artwork — depending on your choice of distance metric, palette, and seed pattern.