# ✦ Crystal Growth Simulator v2.1

A real-time terminal visualization of **Diffusion-Limited Aggregation (DLA)** — watch particles randomly walk and stick together, forming beautiful branching, fractal-like crystalline structures in colorful ASCII art.

## What is DLA?

Diffusion-Limited Aggregation models how particles undergoing random walks (Brownian motion) stick to an aggregate on contact. This simple rule produces stunningly complex, dendritic structures resembling frost, coral, lightning, mineral crystallization, and bacterial colonies.

The key insight: random walkers more easily reach branch tips than crevices, favoring outward growth and creating characteristic fractal morphology.

## Features

### Core Simulation
- **Real-time animation** — watch crystals grow live in your terminal
- **Multiple seed configurations** — center, line, corners, or ring seeds
- **Adjustable physics** — tune stickiness, walker count, and diagonal movement
- **Reproducible** — set `--seed` to recreate specific crystals

### Symmetry Modes
- **Horizontal symmetry** (`--symmetry horizontal`) — mirrors across the vertical axis for snowflake-like patterns
- **Vertical symmetry** (`--symmetry vertical`) — mirrors across the horizontal axis
- **Both** (`--symmetry both`) — 4-fold symmetry for mandala-like crystals

### Export & Saving
- **`--export-json`** — saves full simulation state (grid, parameters, statistics) as JSON
- **Interactive `J` key** — snapshot state to JSON during animation
- **`--snapshot N`** — auto-save plain-text snapshot every N particles
- **`-o`/`--output`** — save final result to file and exit

### Growth Analytics
- **Real-time stats** — particle count, steps, radius, density %, growth rate
- **Accurate density** — counts actual occupied grid cells (not just stick events)
- **Growth history** — tracked internally for analysis (available via JSON export)

### Rendering
- **Beautiful color gradients** — ANSI 24-bit color tracks particle age
- **Multiple character sets** — fancy Unicode, minimal ASCII, or block styles
- **`render_plain()`** — clean text output without ANSI escapes

### Interactive Controls
- **Pause/Resume** — `P` key with visual RUNNING/PAUSED indicator
- **Speed control** — `+`/`-` keys (1–50 steps per frame)
- **Reset** — `R` key restarts the simulation
- **Save** — `S` key saves frame to text file
- **JSON** — `J` key exports state as JSON

### Safety & Quality
- **Input validation** — graceful errors for invalid parameters
- **Path traversal protection** — blocks writing to system directories
- **`~` expansion** — tilde paths work in `-o` and `--export-json`
- **26 unit tests** covering all major features and bug fixes

## Installation

No dependencies required — uses only the Python standard library!

```bash
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

# Lower stickiness = more branching
python3 crystal_growth.py -s 0.3

# Line seed for different morphology
python3 crystal_growth.py -S line

# Horizontal symmetry for snowflake patterns
python3 crystal_growth.py --symmetry horizontal -s 0.4

# 4-fold symmetry for mandala patterns
python3 crystal_growth.py --symmetry both -s 0.3

# Save result to file
python3 crystal_growth.py -o crystal.txt --max-particles 500

# Export as JSON
python3 crystal_growth.py --no-animate -m 200 --export-json state.json

# Auto-snapshot every 100 particles
python3 crystal_growth.py --snapshot 100 -m 500

# Reproducible run
python3 crystal_growth.py --seed 42

# Show version / help
python3 crystal_growth.py --version
python3 crystal_growth.py --help
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
| `--symmetry` | none | Mirror mode: `none`, `horizontal`, `vertical`, `both` |
| `--no-color` | off | Disable colored output |
| `--no-diagonal` | off | Only 4-directional walking |
| `--seed` | random | Random seed for reproducibility |
| `--no-animate` | off | Print final result without animation |
| `-m, --max-particles` | unlimited | Stop after this many particles (0=unlimited) |
| `--speed` | 5 | Simulation steps per frame (1–50) |
| `-o, --output` | none | Save result to file and exit |
| `--export-json` | none | Export simulation state as JSON |
| `--snapshot` | 0 | Auto-save snapshot every N particles (0=disabled) |
| `--version` | — | Show version and exit |

### Interactive Controls

| Key | Action |
|-----|--------|
| `Q` | Quit |
| `P` | Pause / Resume |
| `+` / `-` | Increase / Decrease speed |
| `R` | Reset simulation |
| `S` | Save current frame to text file |
| `J` | Export current state as JSON file |

## How It Works

1. **Seed placement** — Initial particles placed on the grid (center, line, corners, or ring). Seed positions respect the configured symmetry mode.
2. **Walker spawning** — Particles spawn on a circle around the aggregate, ensuring they don't start on occupied cells.
3. **Random walking** — Each particle takes a random step in 4 or 8 directions. If the target cell is occupied, the walker tries other directions.
4. **Sticking** — When a walker lands next to an aggregate particle, it sticks with probability = `stickiness`.
5. **Symmetry** — When a particle sticks, its mirror positions are also filled, creating symmetric growth.
6. **Respawning** — After sticking (or wandering too far), a new walker spawns.
7. **Growth** — Over time, the aggregate develops branching, fractal-like structures.

Particle color encodes age: early particles appear in cool blues/purples, later growth in warm oranges/golds.

## Tips for Beautiful Crystals

- **Lower stickiness** (`-s 0.2` to `-s 0.5`) — more dramatic branching
- **More walkers** (`-w 8+`) — faster growth
- **Line seeds** (`-S line`) — symmetric tree-like structures
- **Corner seeds** (`-S corners`) — four clusters growing from corners
- **Ring seeds** (`-S ring`) — inward growth for different aesthetics
- **Horizontal symmetry** (`--symmetry horizontal`) — snowflake patterns
- **Both symmetry** (`--symmetry both`) — mandala/crystalline structures
- **No diagonals** (`--no-diagonal`) — orthogonal, circuit-board patterns
- Try combining: `python3 crystal_growth.py -S line -s 0.3 -w 10 --symmetry horizontal`

## JSON Export Format

```json
{
  "version": "2.1.0",
  "width": 80,
  "height": 35,
  "particle_count": 250,
  "step_count": 15000,
  "max_radius": 15.3,
  "density_percent": 8.93,
  "stickiness": 1.0,
  "num_walkers": 5,
  "diagonal": true,
  "symmetry": "none",
  "elapsed_seconds": 12.5,
  "grid": [[0, 0, 0, ...], ...]
}
```

The `particle_count` field reflects actual occupied grid cells. The `grid` array contains age values (0 = empty, >0 = order when attached) for reconstruction and analysis.

## Running Tests

```bash
python3 test_crystal_growth.py
```

The test suite (26 tests) covers seed placement, simulation stepping, symmetry, rendering, JSON export, input validation, path security, max_particles enforcement, seed reproducibility, density accuracy, and grid count consistency.

## Changelog

### v2.1.0 — Bug Fix Release
- **Fixed:** `max_particles` limit not enforced in `step()` — simulations now stop growing when the particle limit is reached (was only checked in the CLI animation loop)
- **Fixed:** `particle_count` underreported actual particles with symmetry modes — added `grid_count` to track real occupancy; stats, density, and JSON export now use accurate counts
- **Fixed:** Random seed set after walker creation — `random.seed()` now runs before walkers spawn, making `--seed` actually produce reproducible results
- **Fixed:** Corners seed placed 0 particles on grids smaller than 10×10 — margin now uses `max(1, ...)` to ensure at least one seed block per corner
- **Fixed:** Seed placement didn't respect symmetry mode — `_add_seed()` now applies `_mirror_positions()`, so initial seeds are properly symmetric
- **Fixed:** Growth history tracked stick events instead of actual particles — now uses `grid_count` for accurate analytics
- **Added:** 6 new tests covering all fixed bugs (max_particles enforcement, seed reproducibility, corners on small grids, grid count accuracy, density accuracy, symmetric seed placement)

### v2.0.0
- Symmetry modes, JSON export, auto-snapshots, growth analytics, interactive controls, status bar, `render_plain()`, path validation, walker position optimization

### v1.1.0
- Corners/ring seed fixes, input validation, path traversal protection, `--version` flag

## License

MIT — grow crystals freely!