# ✦ Crystal Growth Simulator v2.0

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

### Core Simulation
- **Real-time animation** — watch crystals grow live in your terminal
- **Multiple seed configurations** — center, line, corners, or ring seeds
- **Adjustable physics** — tune stickiness, walker count, and diagonal movement
- **Reproducible** — set a random seed to recreate specific crystals

### 🆕 Symmetry Modes (v2.0)
- **Horizontal symmetry** (`--symmetry horizontal`) — mirrors growth across the vertical axis for snowflake-like patterns
- **Vertical symmetry** (`--symmetry vertical`) — mirrors growth across the horizontal axis
- **Both** (`--symmetry both`) — 4-fold symmetry for mandala-like crystals

### 🆕 JSON Export
- **`--export-json`** — saves the full simulation state (grid, parameters, statistics) as a JSON file for analysis or reconstruction
- **Interactive JSON save** — press `J` during animation to snapshot state to a file

### 🆕 Auto-Snapshots
- **`--snapshot N`** — automatically saves a plain-text snapshot every N particles

### 🆕 Growth Analytics
- **Real-time statistics** — particle count, steps, radius, density, and growth rate
- **Density tracking** — shows what percentage of the grid is occupied
- **Growth rate** — displays particles grown per 1,000 simulation steps
- **Growth history** — internally tracked for analytics (available via JSON export)

### Rendering
- **Beautiful color gradients** — ANSI 24-bit color tracks particle age
- **Multiple character sets** — fancy Unicode, minimal ASCII, or block styles
- **`render_plain()` API** — clean text output without ANSI escapes

### Interactive Controls
- **Pause/Resume** — `P` key toggles pause with visual indicator
- **Speed control** — `+`/`-` keys adjust simulation speed (1–50)
- **Reset** — `R` key restarts the simulation
- **Save** — `S` key saves current frame to a text file
- **JSON export** — `J` key exports current state as JSON

### Safety & Quality
- **Input validation** — graceful errors for invalid parameters
- **Path traversal protection** — blocks writing to system directories (`/etc/`, `/usr/`, etc.)
- **`~` expansion** — tilde paths work correctly in `-o` and `--export-json`
- **Comprehensive test suite** — 20 unit tests covering all major features

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

# Horizontal symmetry for snowflake-like crystals
python3 crystal_growth.py --symmetry horizontal -s 0.4

# 4-fold symmetry for mandala patterns
python3 crystal_growth.py --symmetry both -s 0.3

# Save result to file (no animation)
python3 crystal_growth.py -o crystal.txt --max-particles 500

# Export simulation state as JSON
python3 crystal_growth.py --no-animate -m 200 --export-json crystal_state.json

# Auto-save snapshots every 100 particles
python3 crystal_growth.py --snapshot 100 -m 500

# Reproducible with a seed
python3 crystal_growth.py --seed 42

# Show version
python3 crystal_growth.py --version

# Show help (all options)
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
| `--no-diagonal` | off | Only allow 4-directional walking (no diagonals) |
| `--seed` | random | Random seed for reproducibility |
| `--no-animate` | off | Print final result without animation |
| `-m, --max-particles` | unlimited | Stop after growing this many particles (0=unlimited) |
| `--speed` | 5 | Simulation steps per frame (min: 1, higher = faster) |
| `-o, --output` | none | Save result to file and exit (blocks system dirs) |
| `--export-json` | none | Export simulation state as JSON file |
| `--snapshot` | 0 | Auto-save a snapshot every N particles (0=disabled) |
| `--version` | — | Show version and exit |

### Interactive Controls (during animation)

| Key | Action |
|-----|--------|
| `Q` | Quit |
| `P` | Pause / Resume |
| `+` / `-` | Increase / Decrease speed |
| `R` | Reset simulation |
| `S` | Save current frame to text file |
| `J` | Export current state as JSON file |

## How It Works

1. **Seed placement** — One or more initial particles are placed on the grid (configurable as center, line, corners, or ring)
2. **Walker spawning** — Multiple particles are spawned on a circle around the existing aggregate, ensuring they don't start on occupied cells
3. **Random walking** — Each particle takes a random step in one of 4 or 8 directions. If the target cell is occupied, the walker tries other directions; if completely surrounded, it respawns
4. **Sticking** — When a walker lands next to an aggregate particle, it sticks with probability = `stickiness`
5. **Symmetry** — When a particle sticks, its mirror positions (based on symmetry mode) are also filled, creating symmetric growth
6. **Respawning** — After sticking (or wandering too far), a new walker spawns to continue the process
7. **Growth** — Over time, the aggregate develops branching, fractal-like structures

The color of each particle encodes its age: early particles appear in cool blues/purples, while later growth appears in warm oranges/golds — letting you visually trace the crystal's growth history.

## Tips for Beautiful Crystals

- **Lower stickiness** (`-s 0.2` to `-s 0.5`) creates more dramatic branching
- **More walkers** (`-w 8` or higher) speeds up growth
- **Line seeds** (`-S line`) create symmetric tree-like structures
- **Corner seeds** (`-S corners`) grow four separate clusters from the corners
- **Ring seeds** (`-S ring`) grow inward for a completely different aesthetic
- **Horizontal symmetry** (`--symmetry horizontal`) creates snowflake-like patterns
- **Both symmetry** (`--symmetry both`) creates mandala/crystalline structures
- **No diagonals** (`--no-diagonal`) produces more orthogonal, circuit-board-like patterns
- Try combining: `python3 crystal_growth.py -S line -s 0.3 -w 10 --symmetry horizontal`

## Examples

```bash
# Classic DLA crystal (default)
python3 crystal_growth.py --seed 42 -m 300

# Fast-growing branching frost
python3 crystal_growth.py -s 0.25 -w 15 -S center --speed 10

# Snowflake symmetry
python3 crystal_growth.py --symmetry horizontal -s 0.4 --seed 42

# Mandala / 4-fold crystal
python3 crystal_growth.py --symmetry both -s 0.3 -w 8

# Slow, delicate growth
python3 crystal_growth.py -s 1.0 -w 1 --speed 2

# Corner growth from all four corners
python3 crystal_growth.py -S corners -w 8

# Circuit board aesthetic
python3 crystal_growth.py --no-diagonal -c minimal -S line

# Export a large crystal with JSON state
python3 crystal_growth.py -W 120 -H 50 -m 800 -o my_crystal.txt --export-json state.json

# Auto-snapshot progress every 200 particles
python3 crystal_growth.py --snapshot 200 -m 1000
```

## JSON Export Format

The `--export-json` flag saves the complete simulation state:

```json
{
  "version": "2.0.0",
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

The `grid` array contains the age of each particle (0 = empty, >0 = age order when attached), which can be used to reconstruct and analyze the crystal.

## Running Tests

```bash
python3 test_crystal_growth.py
```

The test suite covers seed placement, simulation stepping, symmetry modes, rendering, JSON export, input validation, and path security.

## Changelog

### v2.0.0
- **New:** Symmetry modes (`--symmetry horizontal|vertical|both`) for snowflake and mandala-like crystals
- **New:** JSON export (`--export-json`) saves full simulation state for analysis
- **New:** Auto-snapshots (`--snapshot N`) periodically saves crystal progress
- **New:** Growth analytics — density, growth rate, and elapsed time in stats
- **New:** Interactive `J` key for JSON export during animation
- **New:** Status bar showing RUNNING/PAUSED state during animation
- **New:** `render_plain()` method for clean ANSI-free text output
- **Improved:** Walker position lookup optimized from O(n) to O(1) using a set
- **Improved:** `validate_output_path` now handles `~` expansion correctly
- **Improved:** Comprehensive docstrings on all classes and methods
- **Improved:** Version number displayed in title bar
- **New:** 20 unit tests covering all major features

### v1.1.0
- Fixed corners seed mode (walkers couldn't reach corner seeds)
- Fixed ring seed mode explosive growth (spawn on occupied cell check)
- Fixed walker stuck-in-corner handling
- Added input validation for all parameters
- Added path traversal protection on `-o` flag
- Added `--version` flag

## License

MIT — grow crystals freely!