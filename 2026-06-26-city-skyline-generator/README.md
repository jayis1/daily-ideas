# 🏙️ Procedural City Skyline Generator

A CLI tool that generates detailed, atmospheric ASCII city skylines with buildings, weather effects, time-of-day lighting, and varied architectural styles. Each run produces a unique city — no two skylines are the same.

![night skyline](https://img.shields.io/badge/time-night-9b59b6) ![day skyline](https://img.shields.io/badge/time-day-3498db)

## What It Does

Generates a full-color (or plain-text) city skyline including:

- **Procedural buildings** with window grids, antennas, spires, and varied widths/heights
- **6 architectural styles**: modern, art deco, gothic, industrial, brutalist, residential
- **4 times of day**: dawn, day, dusk, night — each with distinct color palettes
- **6 weather conditions**: clear, cloudy, rain, snow, fog, storm
- **Celestial objects**: stars, moon phases, sun with glow halos
- **Adjustable density**: from sparse suburbs to packed downtowns
- **Reproducible output** via seed parameter
- **Random city names and populations** in the stats footer

## Features

| Feature | Description |
|---|---|
| 🌙 Time of Day | Dawn (warm orange), day (bright blue), dusk (purple-red), night (dark blue) |
| 🌧️ Weather | Clear skies, clouds, rain, snow, fog, thunderstorms |
| 🏗️ Architecture | Modern glass, art deco towers, gothic spires, industrial blocks, brutalist slabs, residential homes |
| 🎨 ANSI Colors | Full 256-color palette for atmospheric rendering |
| 🔒 Seeded RNG | Deterministic output with `--seed` for sharing favorite cities |
| 📏 Custom Width | Generate skylines from 40 to 200+ characters wide |
| 🏙️ Density Control | From open suburbs (0.2) to dense metropolis (1.0) |

## Installation

```bash
# No dependencies needed — uses only the Python standard library
git clone <repo-url>
cd 2026-06-26-city-skyline-generator
```

Requires Python 3.7+ (uses only standard library modules: `random`, `argparse`, `sys`).

## Usage

```bash
# Default: 80-char night skyline with clear weather
python skyline.py

# Sunny daytime city
python skyline.py --time day

# Gothic city in a thunderstorm
python skyline.py --style gothic --weather storm

# Dawn with rain, wide panoramic view
python skyline.py --time dawn --weather rain --width 120

# Reproducible output for sharing
python skyline.py --seed 42

# Plain text (no ANSI colors)
python skyline.py --no-color

# List all available options
python skyline.py --list
```

## Command Line Options

| Flag | Default | Description |
|---|---|---|
| `-w`, `--width` | 80 | Skyline width in characters |
| `-t`, `--time` | night | Time: `dawn`, `day`, `dusk`, `night` |
| `--weather` | clear | Weather: `clear`, `cloudy`, `rain`, `snow`, `fog`, `storm` |
| `-s`, `--style` | mixed | Architecture: `modern`, `art_deco`, `gothic`, `industrial`, `brutalist`, `residential`, `mixed` |
| `-d`, `--density` | 0.7 | Building density (0.0–1.0) |
| `--seed` | random | Random seed for reproducibility |
| `--no-color` | off | Disable ANSI color codes |
| `--list` | — | List available styles and options |
| `--version` | — | Show version number |

## Examples

### Night skyline
```
python skyline.py --time night --seed 42
```

### Day with rain
```
python skyline.py --time day --weather rain --seed 7
```

### Dense brutalist city at dusk
```
python skyline.py --time dusk --style brutalist --density 0.9 --width 100
```

### Gothic city in a snowstorm
```
python skyline.py --style gothic --weather snow --time night --seed 13
```

## Running Tests

```bash
python test_skyline.py
```

Runs 14 tests covering: default output, color/no-color modes, all time options, all weather options, all style options, custom widths, density, seed reproducibility, different seed divergence, list/version flags, building detection, and stats line format.

## How It Works

1. **Canvas creation**: A 2D grid (default 16 rows × 80 cols) is initialized with sky gradients based on the chosen time of day
2. **Building generation**: Buildings are placed left-to-right with height influenced by distance from center (taller downtown, shorter outskirts), following the `--density` parameter for spacing
3. **Each building** has: randomized height/width, window grid (lit/dim/dark/bright), optional antenna/spire, style-specific body and edge characters
4. **Weather overlay**: Rain drops (·˙), snowflakes (✻❄), fog patches (░▒), clouds, and lightning (⚡) are scattered across the sky
5. **Celestial objects**: Stars, moon phases (●☽◑◕○), and sun with glow halos are placed based on time
6. **ANSI colors**: Each time-of-day theme defines colors for sky gradients, building edges, window types, and ground — creating atmospheric depth
7. **Stats footer**: A randomly generated city name, population, building count, time, and weather are displayed below the skyline

## License

MIT