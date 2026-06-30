# 🏔️ ASCII Terrain Flyover

A procedurally generated 3D-like terrain flyover rendered entirely in your terminal using ANSI 256-color codes and Unicode characters. Soar over mountains, oceans, forests, and plains — all generated in real-time from Perlin noise.

![Terminal](https://img.shields.io/badge/platform-terminal-green) ![Python](https://img.shields.io/badge/python-3.7+-blue) ![License](https://img.shields.io/badge/license-MIT-yellow)

## Features

- **Real-time flyover animation** — the camera gently banks and sweeps across procedurally generated terrain
- **Perlin noise terrain generation** — multi-octave noise creates realistic terrain with oceans, beaches, plains, forests, mountains, and alpine peaks
- **Biome-aware rendering** — different colors and characters for each terrain type (deep ocean `~`, shallow water `≈`, beach `.`, grass `"`, forest `♣`, mountain `^`, snow `*`)
- **Sky with clouds** — gradient sky with procedurally generated cloud formations and a glowing sun
- **Distance fog** — terrain fades into atmospheric haze at long range
- **Hill shading** — simple lighting makes terrain features pop
- **Top-down map mode** — view the terrain from above with `--map`
- **Status bar** — shows coordinates, heading, current biome, seed, altitude, and speed
- **Deterministic seeds** — share a seed number to reproduce the same terrain
- **Configurable** — adjust speed, altitude, FPS, duration, and more

## How It Works

1. **Perlin Noise** generates 2D heightmaps with multi-octave layering for realistic terrain
2. **Perspective projection** converts height values to a first-person view with a horizon line
3. **Ray marching** samples terrain at increasing distances for each screen column
4. **ANSI 256-color** escape codes color each cell by biome type and fog distance
5. **Unicode characters** represent terrain features at different zoom levels

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

# Limit duration (in seconds)
python3 terrain_flyover.py --duration 30

# Higher framerate
python3 terrain_flyover.py --fps 30

# Combine options
python3 terrain_flyover.py --seed 123 --speed 1.5 --altitude 0.7 --fps 25
```

### Map mode

View a top-down minimap of the terrain:

```bash
python3 terrain_flyover.py --map
python3 terrain_flyover.py --map --seed 42
python3 terrain_flyover.py --map --scale 0.1  # zoomed in
python3 terrain_flyover.py --map --scale 0.5  # zoomed out
```

### Controls

- Press **Ctrl+C** to stop the animation at any time
- On exit, the script displays final position, seed, frames rendered, and duration

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--seed` | random | Random seed for terrain generation |
| `--speed` | 1.0 | Flight speed multiplier |
| `--altitude` | 0.6 | Camera altitude (0.1–1.0) |
| `--fps` | 20 | Target frames per second |
| `--duration` | ∞ | Duration in seconds |
| `--map` | off | Show top-down map instead of flyover |
| `--scale` | 0.2 | Map zoom level (map mode only) |

## Biomes

| Character | Biome | Height Range |
|-----------|-------|-------------|
| `~ ≈ ∽` | Ocean | 0.00–0.35 |
| `. , ·` | Beach/Shallows | 0.35–0.38 |
| `v " \|` | Plains/Grass | 0.38–0.60 |
| `♠ ♣ ¶` | Forest | 0.60–0.72 |
| `^ ▲ ⛰` | Mountain | 0.72–0.82 |
| `* ✦ ❄` | Alpine/Snow | 0.82–1.00 |

## Example Output

Flyover mode renders a perspective view with sky, fog, and terrain:

```
      ░░░░░▒▒▒▓▓▓▓▓▒▒▒░░░░░░░  ░░  ░░    ░░░░░░░░░░░░░
          ░░▒▓████████▓▒░░░░░░░░  ░░░░░░░░░░░░░░░░░░░░░░
""""""vvvvvv""""""""""vvvv♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣^^^^^^^♣♣♣♣♣♣
""""""vvvvvv""""""""""vvvv♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣^^^^^^^♣♣♣♣♣♣♣
"""""""vvvvvv""""""""vvvvv♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣^^^^^^♣♣♣♣♣♣♣♣
  POS (142,87)  HDG 15°  BIOME Forest  SEED 42  ALT 0.6  SPD 1.0×
```

Map mode renders a top-down view:

```
♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣
♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣
♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣
▶♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣♣
```

## Implementation Notes

- **Perlin noise**: Custom implementation with permutation tables and gradient interpolation
- **Octave noise**: 6 octaves with configurable persistence and lacunarity for realistic terrain detail
- **Power curve**: Applied to height values to create more dramatic peaks and deeper ocean trenches
- **Hill shading**: Compares neighboring height values to simulate directional lighting
- **Fog**: Distance-based atmospheric perspective using alpha blending over ANSI palette
- **Clouds**: Second noise instance offset to create independent cloud formations
- **Camera path**: Sinusoidal heading oscillation creates a natural banking/sweeping flight path

## License

MIT