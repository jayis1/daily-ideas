# 🏔️ ASCII Terrain Flyover

A procedurally generated 3D-like terrain flyover rendered entirely in your terminal using ANSI 256-color codes and Unicode characters. Soar over mountains, oceans, forests, and plains — all generated in real-time from Perlin noise.

![Terminal](https://img.shields.io/badge/platform-terminal-green) ![Python](https://img.shields.io/badge/python-3.7+-blue) ![License](https://img.shields.io/badge/license-MIT-yellow) ![Version](https://img.shields.io/badge/version-1.1.1-orange)

## Features

- **Real-time flyover animation** — the camera gently banks and sweeps across procedurally generated terrain
- **Perlin noise terrain generation** — multi-octave noise creates realistic terrain with oceans, beaches, plains, forests, mountains, and alpine peaks
- **Biome-aware rendering** — different colors and characters for each terrain type (deep ocean `~`, shallow water `≈`, beach `.`, grass `"`, forest `♣`, mountain `^`, snow `*`)
- **Day/night cycle** — fly at any hour with `--hour` (midnight, sunset, noon — each with unique sky palettes and terrain tinting)
- **Animated water** — ocean and shallow water characters cycle through wave patterns
- **Sky with clouds** — gradient sky with procedurally generated cloud formations and a glowing sun/moon
- **Distance fog** — terrain fades into atmospheric haze at long range (with darker fog at night)
- **Hill shading** — simple directional lighting makes terrain features pop
- **Compass heading** — status bar shows heading direction (N, NE, E, etc.)
- **Top-down map mode** — view the terrain from above with `--map`, now with time-of-day support
- **Minimap overlay** — see a small map in the corner during flyover with `--minimap`
- **Interactive controls** — use WASDQE keys to fly manually with `--interactive`
- **Screenshot export** — save a single frame as a plain-text file with `--screenshot`
- **Status bar** — shows coordinates, compass heading, current biome, seed, altitude, speed, and time of day
- **Deterministic seeds** — share a seed number to reproduce the same terrain
- **Configurable** — adjust speed, altitude, FPS, duration, time-of-day, and more
- **`--version` flag** — prints the version number
- **Comprehensive test suite** — 55 tests covering noise, color, rendering, CLI, and regression tests for fixed bugs

## What's New

### v1.1.1 (Bug Fix Release)

- 🐛 **Fixed: Division by zero crash when `fog_dist=0`** — `height_to_char()` and `fog_factor` calculation now guard against zero fog distance
- 🐛 **Fixed: Interactive mode WASDQE keys had no effect** — `_keys_held` was cleared before `render_frame()` read it; now cleared after rendering instead
- 🐛 **Fixed: Q key did nothing in interactive mode** — the dead `if key.lower() == 'q' and key.isupper(): pass` branch was removed; Q now correctly decreases altitude via `_keys_held`
- 🐛 **Fixed: Minimap overlay garbled ANSI escape sequences** — `_overlay_minimap()` was slicing raw ANSI strings at byte offsets, splitting escape codes in half; now properly parses visual cells before overlaying
- 🐛 **Fixed: `render_minimap()` position marker parser was fragile** — replaced the ad-hoc ANSI parser with the robust `_parse_ansi_cells()` / `_cells_to_string()` methods
- ✅ Added 11 regression tests for all fixed bugs
- 🧹 Added `_parse_ansi_cells()` and `_cells_to_string()` helper methods for correct ANSI-aware string manipulation

### v1.1.0 (Feature Release)

- 🌅 Day/night cycle (`--hour`)
- 🌊 Animated water characters
- 🧭 Compass heading in status bar
- 🗺️ Minimap overlay (`--minimap`)
- ⌨️ Interactive mode (`--interactive`)
- 📸 Screenshot export (`--screenshot`)
- 🏷️ `--version` flag
- 🧪 44 tests

## How It Works

1. **Perlin Noise** generates 2D heightmaps with multi-octave layering for realistic terrain
2. **Perspective projection** converts height values to a first-person view with a horizon line
3. **Ray marching** samples terrain at increasing distances for each screen column
4. **ANSI 256-color** escape codes color each cell by biome type and fog distance
5. **Unicode characters** represent terrain features at different zoom levels
6. **Day/night interpolation** blends between three sky palettes (day, sunset, night) based on the `--hour` parameter

## Installation

No dependencies needed — uses only the Python standard library:

```bash
# Just run it directly
python3 terrain_flyover.py

# Or clone this folder
cd ~/daily-ideas/2026-06-30-ascii-terrain-flyover
python3 terrain_flyover.py
```

Requires a terminal that supports ANSI 256-color codes (most modern terminals do).

## Usage

### Flyover mode (default)

```bash
# Start with a random seed
python3 terrain_flyover.py

# Use a specific seed for reproducible terrain
python3 terrain_flyover.py --seed 42

# Fly faster
python3 terrain_flyover.py --speed 2.0

# Higher altitude for a bird's-eye view
python3 terrain_flyover.py --altitude 0.9

# Low altitude for dramatic terrain
python3 terrain_flyover.py --altitude 0.3

# Fly at sunset
python3 terrain_flyover.py --hour 19

# Fly at night
python3 terrain_flyover.py --hour 2

# Limit duration (in seconds)
python3 terrain_flyover.py --duration 30

# Higher framerate
python3 terrain_flyover.py --fps 30

# Show minimap overlay
python3 terrain_flyover.py --minimap

# Interactive mode (use WASDQE keys)
python3 terrain_flyover.py --interactive

# Combine options
python3 terrain_flyover.py --seed 123 --speed 1.5 --altitude 0.7 --fps 25 --hour 19 --minimap
```

### Map mode

View a top-down minimap of the terrain:

```bash
python3 terrain_flyover.py --map
python3 terrain_flyover.py --map --seed 42
python3 terrain_flyover.py --map --hour 20       # nighttime map
python3 terrain_flyover.py --map --scale 0.1     # zoomed in
python3 terrain_flyover.py --map --scale 0.5     # zoomed out
```

### Screenshot mode

Save a single frame to a plain-text file:

```bash
python3 terrain_flyover.py --screenshot terrain.txt
python3 terrain_flyover.py --screenshot night.txt --hour 2
python3 terrain_flyover.py --screenshot sunset.txt --hour 19 --seed 42
```

### Interactive Controls

When running with `--interactive`, use these keys:

| Key | Action |
|-----|--------|
| **W** | Speed up |
| **S** | Slow down |
| **A** | Turn left |
| **D** | Turn right |
| **Q** | Decrease altitude |
| **E** | Increase altitude |
| **X** | Exit |
| **Ctrl+C** | Exit |

### Controls

- Press **Ctrl+C** to stop the animation at any time
- On exit, the script displays final position, heading, seed, frames rendered, and duration

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--seed` | random | Random seed for terrain generation |
| `--speed` | 1.0 | Flight speed multiplier |
| `--altitude` | 0.6 | Camera altitude (0.1–1.0) |
| `--fps` | 20 | Target frames per second |
| `--duration` | ∞ | Duration in seconds |
| `--hour` | 12.0 | Time of day (0–24). 0=midnight, 6=dawn, 12=noon, 19=sunset |
| `--map` | off | Show top-down map instead of flyover |
| `--scale` | 0.2 | Map zoom level (map mode only) |
| `--interactive` | off | Enable WASDQE keyboard controls |
| `--minimap` | off | Show minimap overlay during flyover |
| `--screenshot` | — | Save a single frame to FILE and exit |
| `--version` | — | Print version and exit |

## Biomes

| Character | Biome | Height Range |
|-----------|-------|-------------|
| `~ ≈ ∽ ∿` | Ocean | 0.00–0.28 |
| `≈ ∽ ∿` | Shallows | 0.28–0.35 |
| `. , ·` | Beach | 0.35–0.40 |
| `v " \|` | Plains/Grass | 0.40–0.60 |
| `♠ ♣ ¶` | Forest | 0.60–0.72 |
| `^ ▲ ⛰` | Mountain | 0.72–0.82 |
| `* ✦ ❄` | Alpine/Snow | 0.82–1.00 |

## Example Output

Flyover mode renders a perspective view with sky, fog, terrain, and animated water:

```
      ░░░░░▒▒▒▓▓▓▓▓▒▒▒░░░░░░░  ░░  ░░    ░░░░░░░░░░░░░
          ░░▒▓████████▓▒░░░░░░░░  ░░░░░░░░░░░░░░░░░░░░░░
""""""vvvvvv""""""""""vvvv♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣^^^^^^^♣♣♣♣♣♣
""""""vvvvvv""""""""""vvvv♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣^^^^^^♣♣♣♣♣♣♣♣
  POS (142,87)  HDG 15° NE  BIOME Forest  SEED 42  ALT 0.6  SPD 1.0×  TIME 12:00
```

Map mode renders a top-down view:

```
♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣
♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣
                              ▶♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣
```

## Testing

```bash
python3 -m pytest test_terrain_flyover.py -v
```

55 tests covering Perlin noise, color blending, height mapping, terrain rendering, day/night palettes, screenshot export, map mode, sky rendering, CLI arguments, and regression tests for all fixed bugs.

## Changelog

### v1.1.1
- Fixed crash when `fog_dist=0` (division by zero in `height_to_char` and `fog_factor`)
- Fixed interactive mode WASDQE keys having no effect (`_keys_held` cleared before use)
- Fixed Q key being a no-op (dead `pass` branch removed; Q now decreases altitude)
- Fixed minimap overlay garbling ANSI escape sequences (byte-offset slicing replaced with visual-cell parsing)
- Fixed fragile ANSI parser in `render_minimap()` (replaced with `_parse_ansi_cells()`)
- Added `_parse_ansi_cells()` and `_cells_to_string()` helper methods for ANSI-aware string manipulation
- Added 11 regression tests

### v1.1.0
- Added day/night cycle, animated water, compass heading, minimap overlay, interactive mode, screenshot export, `--version` flag
- Added 44 tests

### v1.0.0
- Initial release

## License

MIT