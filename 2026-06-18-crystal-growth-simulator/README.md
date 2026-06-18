# ✦ Crystal Growth Simulator

A real-time terminal visualization of **Diffusion-Limited Aggregation (DLA)** — the process where particles randomly walking through space stick together on contact, forming beautiful, branching, fractal-like crystalline structures.

Watch crystals grow before your eyes in colorful ASCII art!

## What is DLA?

Diffusion-Limited Aggregation is a process first modeled by T.A. Witten and L.M. Sander in 1981. Particles undergo random walks (Brownian motion), and when they touch an existing aggregate, they stick permanently. This simple rule produces stunningly complex, dendritic (tree-like) structures that resemble:

- Frost patterns on windows
- Coral growth
- Lightning bolts
- Mineral crystallization
- Bacterial colonies

The key insight: because random walkers are more likely to reach the tips of existing branches before penetrating deep crevices, the growth favors outward branching — creating the characteristic fractal morphology.

## Features

- **Real-time animation** — watch crystals grow live in your terminal
- **Multiple seed configurations** — center, line, corners, or ring seeds
- **Adjustable physics** — tune stickiness, walker count, and diagonal movement
- **Beautiful color gradients** — ANSI 24-bit color tracks particle age
- **Interactive controls** — pause, speed up, reset, or save mid-simulation
- **Multiple character sets** — fancy Unicode, minimal ASCII, or block styles
- **Export to file** — save final crystal as plain text for sharing
- **Reproducible** — set a random seed to recreate specific crystals
- **Input validation** — graceful errors for invalid parameters
- **Safe file output** — path traversal protection on the `-o` flag

## Installation

No dependencies required — uses only the Python standard library!

```bash
# Just clone and run
cd ~/daily-ideas/2026-06-18-crystal-growth-simulator
python3 crystal_growth.py
```

## Usage

### Basic (animated, real-time growth)
```bash
python3 crystal_growth.py
```

### With options
```bash
# Larger crystal with more walkers
python3 crystal_growth.py -W 100 -H 45 -w 10

# Lower stickiness = more branching (particles don't always stick)
python3 crystal_growth.py -s 0.3

# Line seed for different morphology
python3 crystal_growth.py -S line

# Ring seed for circular growth patterns
python3 crystal_growth.py -S ring -w 8

# Corner seeds grow from all four corners
python3 crystal_growth.py -S corners

# Save result to file (no animation)
python3 crystal_growth.py -o crystal.txt --max-particles 500

# Reproducible with a seed
python3 crystal_growth.py --seed 42

# Show version
python3 crystal_growth.py --version
```

### Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `-W, --width` | 80 | Grid width (auto-detects terminal, min: 3) |
| `-H, --height` | 35 | Grid height (auto-detects terminal, min: 3) |
| `-w, --walkers` | 5 | Number of simultaneous random walkers (min: 1) |
| `-s, --stickiness` | 1.0 | Probability of sticking on contact (0.0–1.0, exclusive of 0) |
| `-S, --seed-pos` | center | Seed shape: `center`, `line`, `corners`, `ring` |
| `-c, --charset` | fancy | Character style: `fancy`, `minimal`, `bw` |
| `--no-color` | off | Disable colored output |
| `--no-diagonal` | off | Only allow 4-directional walking (no diagonals) |
| `--seed` | random | Random seed for reproducibility |
| `--no-animate` | off | Print final result without animation |
| `-m, --max-particles` | unlimited | Stop after growing this many particles (0=unlimited) |
| `--speed` | 5 | Simulation steps per frame (min: 1, higher = faster) |
| `-o, --output` | none | Save result to file and exit (blocks system dirs) |
| `--version` | — | Show version and exit |

### Interactive Controls (during animation)

| Key | Action |
|-----|--------|
| `Q` | Quit |
| `P` | Pause / Resume |
| `+` / `-` | Increase / Decrease speed |
| `R` | Reset simulation |
| `S` | Save current frame to file |

## How It Works

1. **Seed placement** — One or more initial particles are placed on the grid (configurable as center, line, corners, or ring)
2. **Walker spawning** — Multiple particles are spawned on a circle around the existing aggregate, ensuring they don't start on occupied cells
3. **Random walking** — Each particle takes a random step in one of 4 or 8 directions. If the target cell is occupied, the walker tries other directions; if completely surrounded, it respawns
4. **Sticking** — When a walker lands next to an aggregate particle, it sticks with probability = `stickiness`
5. **Respawning** — After sticking (or wandering too far), a new walker spawns to continue the process
6. **Growth** — Over time, the aggregate develops branching, fractal-like structures

The color of each particle encodes its age: early particles appear in cool blues/purples, while later growth appears in warm oranges/golds — letting you visually trace the crystal's growth history.

## Tips for Beautiful Crystals

- **Lower stickiness** (`-s 0.2` to `-s 0.5`) creates more dramatic branching
- **More walkers** (`-w 8` or higher) speeds up growth
- **Line seeds** (`-S line`) create symmetric tree-like structures
- **Corner seeds** (`-S corners`) grow four separate clusters from the corners
- **Ring seeds** (`-S ring`) grow inward for a completely different aesthetic
- **No diagonals** (`--no-diagonal`) produces more orthogonal, circuit-board-like patterns
- Try combining: `python3 crystal_growth.py -S line -s 0.3 -w 10`

## Examples

```
# Classic DLA crystal (default)
python3 crystal_growth.py --seed 42 -m 300

# Fast-growing branching frost
python3 crystal_growth.py -s 0.25 -w 15 -S center --speed 10

# Slow, delicate growth
python3 crystal_growth.py -s 1.0 -w 1 --speed 2

# Corner growth from all four corners
python3 crystal_growth.py -S corners -w 8

# Circuit board aesthetic
python3 crystal_growth.py --no-diagonal -c minimal -S line

# Export a large crystal
python3 crystal_growth.py -W 120 -H 50 -m 800 -o my_crystal.txt
```

## Bug Fixes (v1.1.0)

This version fixes several bugs found in the original release:

- **Corners seed mode now works** — Walkers couldn't reach corner seeds because the kill-distance was too small. Fixed by increasing `max_dist` to accommodate all seed types
- **Ring seed mode no longer causes explosive growth** — Walkers spawning on ring particles would instantly stick, creating thousands of phantom particles. Fixed by checking spawn positions aren't on occupied cells
- **Walkers on occupied cells are now respawned** — A walker that ends up on an aggregate cell (through spawning or movement) is immediately respawned to an empty cell
- **Walker stuck-in-corner handling** — When a walker's random walk target is occupied, it now tries all directions before respawning, instead of getting stuck indefinitely
- **Input validation** — Width/height < 3, walkers < 1, stickiness ≤ 0 or > 1, negative max-particles, and speed < 1 are now rejected with clear error messages
- **Path traversal protection** — The `-o` flag no longer allows writing to system directories like `/etc/`
- **`--version` flag added** — Shows version number

## License

MIT — grow crystals freely!