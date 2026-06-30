# 🏔️ ASCII Terrain Flyover

A procedurally generated 3D-like terrain flyover rendered entirely in your terminal using ANSI 256-color codes and Unicode characters. Soar over mountains, oceans, forests, and plains — all generated in real-time from Perlin noise.

![Terminal](https://img.shields.io/badge/platform-terminal-green) ![Python](https://img.shields.io/badge/python-3.7+-blue) ![License](https://img.shields.io/badge/license-MIT-yellow) ![Version](https://img.shields.io/badge/version-1.1.0-orange)

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
- **Comprehensive test suite** — 44 tests covering noise, color, rendering, and CLI

## What's New in v1.1.0

- 🌅 **Day/night cycle** — `--hour` parameter changes sky, terrain tinting, and fog colors (try `--hour 0` for midnight, `--hour 19` for sunset)
- 🌊 **Water animation** — ocean and shallow water characters animate with wave patterns
- 🧭 **Compass heading** — status bar now shows compass direction (N/NE/E/SE/S/SW/W/NW)
- 🗺️ **Minimap overlay** — `--minimap` shows a live top-down map in the corner during flyover
- ⌨️ **Interactive mode** — `--interactive` enables WASDQE keyboard controls for manual flight
- 📸 **Screenshot mode** — `--screenshot FILE` saves a single plain-text frame to a file
- 🏷️ **`--version`** flag added
- 🐛 **Fixed minimap position marker** — the ▶ marker now correctly replaces the center character
- 🧪 **Full test suite** — 44 tests covering all major functionality
- 📝 **Type hints and improved documentation** throughout the codebase

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
""""""vvvvvv""""""""""vvvv♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣^^^^^^♣♣♣♣♣♣♣
  POS (142,87)  HDG 15° NE  BIOME Forest  SEED 42  ALT 0.6  SPD 1.0×  TIME 12:00
```

Night mode (`--hour 2`):

```
      ░░░░░▒▒▒▓▓▓▓▓▒▒▒░░░░░░░  ░░  ░░    ░░░░░░░░░░░░░
  POS (142,87)  HDG 15° NE  BIOME Ocean  SEED 42  ALT 0.6  SPD 1.0×  TIME 02:00
```

Map mode renders a top-down view:

```
♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣
♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣
                              ▶♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣
```

## Testing

```bash
python3 -m pytest test_terrain_flyover.py -v
```

44 tests covering Perlin noise, color blending, height mapping, terrain rendering, day/night palettes, screenshot export, map mode, sky rendering, and CLI arguments.

## Implementation Notes

- **Perlin noise**: Custom implementation with permutation tables and gradient interpolation
- **Octave noise**: 6 octaves with configurable persistence and lacunarity for realistic terrain detail
- **Power curve**: Applied to height values to create more dramatic peaks and deeper ocean trenches
- **Hill shading**: Compares neighboring height values to simulate directional lighting
- **Fog**: Distance-based atmospheric perspective using alpha blending over ANSI palette (darkens at night)
- **Clouds**: Second noise instance offset to create independent cloud formations
- **Camera path**: Sinusoidal heading oscillation creates a natural banking/sweeping flight path (or manual WASDQE control)
- **Day/night**: Three palettes (day, sunset, night) interpolated by hour — terrain tints darker at night, sky gradient shifts, and fog turns dark
- **Water animation**: Ocean/shallows characters cycle through `~≈∽∿` based on frame count and distance
- **Compass**: Heading in radians converted to 8-direction compass bearing
- **Minimap**: Inline overlay parses ANSI-coded strings to insert the ▶ position marker

## License

MIT