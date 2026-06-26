# 🏙️ Procedural City Skyline Generator

A CLI tool that generates detailed, atmospheric ASCII city skylines with buildings, weather effects, time-of-day lighting, varied architectural styles, neon signs, waterfront reflections, and SVG export. Each run produces a unique city — no two skylines are the same.

![night](https://img.shields.io/badge/time-night-9b59b6) ![day](https://img.shields.io/badge/time-day-3498db) ![waterfront](https://img.shields.io/badge/feature-waterfront-2eaadc) ![svg](https://img.shields.io/badge/export-svg-green)

## What It Does

Generates a full-color (or plain-text) city skyline including:

- **Procedural buildings** with window grids, antennas, spires, and varied widths/heights
- **6 architectural styles**: modern, art deco, gothic, industrial, brutalist, residential
- **4 times of day**: dawn, day, dusk, night — each with distinct color palettes
- **6 weather conditions**: clear, cloudy, rain, snow, fog, storm
- **Celestial objects**: stars, moon phases, sun with glow halos
- **Sky life**: birds at dawn/day, airplanes with contrails at night/dusk
- **Neon signs**: glowing sign characters on buildings at night and dusk
- **Waterfront mode**: water with building reflections and wave effects
- **SVG export**: generate scalable vector graphics of the skyline
- **Save to file**: write plain-text output to a file (ANSI codes automatically stripped)
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
| 📏 Custom Width | Generate skylines from 20 to 300 characters wide |
| 🏙️ Density Control | From open suburbs (0.1) to dense metropolis (1.0) |
| 💡 Neon Signs | Glowing sign characters on buildings at night/dusk |
| 🐦 Sky Life | Birds during day/dawn, airplanes with contrails at night/dusk |
| 🌊 Waterfront | Water with building reflections and wave effects (`--water`) |
| 📊 SVG Export | Scalable vector graphics output (`--svg file.svg`) |
| 💾 Save to File | Write plain-text output to file (`--save file.txt`) |
| 📋 Enhanced `--list` | Shows style descriptions and special options |

## Installation

```bash
# No dependencies needed — uses only the Python standard library
git clone <repo-url>
cd 2026-06-26-city-skyline-generator
```

Requires Python 3.7+ (uses only standard library modules: `random`, `argparse`, `sys`, `os`).

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

# Waterfront city with reflections
python skyline.py --water

# Dense brutalist waterfront at dusk
python skyline.py --time dusk --style brutalist --density 0.9 --water --width 100

# Export as SVG
python skyline.py --seed 42 --svg city.svg

# Save plain text to file (ANSI codes are automatically stripped)
python skyline.py --seed 42 --save skyline.txt

# List all available options with descriptions
python skyline.py --list
```

## Command Line Options

| Flag | Default | Description |
|---|---|---|
| `-w`, `--width` | 80 | Skyline width in characters (20–300) |
| `-t`, `--time` | night | Time: `dawn`, `day`, `dusk`, `night` |
| `--weather` | clear | Weather: `clear`, `cloudy`, `rain`, `snow`, `fog`, `storm` |
| `-s`, `--style` | mixed | Architecture: `modern`, `art_deco`, `gothic`, `industrial`, `brutalist`, `residential`, `mixed` |
| `-d`, `--density` | 0.7 | Building density (0.1–1.0) |
| `--seed` | random | Random seed for reproducibility |
| `--no-color` | off | Disable ANSI color codes |
| `--water` | off | Add waterfront with building reflections |
| `--svg` FILE | — | Export skyline as SVG file |
| `--save` FILE | — | Save plain-text output to file (always stripped of ANSI codes) |
| `--list` | — | List available styles and options |
| `--version` | — | Show version number (1.2.0) |

## Examples

### Night skyline with waterfront
```
python skyline.py --time night --water --seed 42
```

### Day with rain
```
python skyline.py --time day --weather rain --seed 7
```

### Dense brutalist city at dusk
```
python skyline.py --time dusk --style brutalist --density 0.9 --width 100
```

### Gothic city in a snowstorm, exported as SVG
```
python skyline.py --style gothic --weather snow --time night --seed 13 --svg gothic_city.svg
```

### Full-featured waterfront at dawn
```
python skyline.py --time dawn --weather fog --water --width 120 --seed 99
```

## Running Tests

```bash
python test_skyline.py
```

Runs 47 tests covering: default output, color/no-color modes, all time options, all weather options, all style options, custom widths, width validation, density, seed reproducibility, different seed divergence, list/version/help flags, building detection, stats line format, waterfront mode, SVG export, save to file, neon signs, sky life (birds/planes), edge case validation, and regression tests for all fixed bugs.

## How It Works

1. **Canvas creation**: A 2D grid (default 14 sky rows + 2 ground rows + optional 4 water rows × width cols) is initialized with sky gradients based on the chosen time of day
2. **Building generation**: Buildings are placed left-to-right with height influenced by distance from center (taller downtown, shorter outskirts), following the `--density` parameter for spacing. Buildings are constrained to never extend past the canvas width.
3. **Each building** has: randomized height/width, window grid (lit/dim/dark/bright), optional antenna/spire, style-specific body and edge characters, and optional neon sign
4. **Sky life**: Birds appear as small V-shaped flocks during day/dawn; airplanes with contrails appear at night/dusk
5. **Weather overlay**: Rain drops (·˙), snowflakes (✻❄), fog patches (░▒), clouds, and lightning (⚡) are scattered across the sky
6. **Celestial objects**: Stars, moon phases (●☽◑◕○), and sun with glow halos are placed based on time
7. **Neon signs**: On night/dusk, wider buildings get randomized neon characters (♠♥♦♣★☆◆◇) in bright colors
8. **Waterfront**: When enabled, 4 rows of water appear below ground with wave characters and fading building reflections
9. **ANSI colors**: Each time-of-day theme defines colors for sky gradients, building edges, window types, ground, water, and neon — creating atmospheric depth
10. **Stats footer**: A randomly generated city name, population, building count, time, weather, and waterfront indicator are displayed below the skyline
11. **SVG export**: The `--svg` option renders the skyline as a scalable vector graphic with sky gradients, building rectangles, window details, antennas, and spires positioned correctly relative to buildings
12. **File saving**: The `--save` option always writes plain text (ANSI codes are stripped), ensuring saved files are clean and readable

## Bug Fixes (v1.2.0)

- **Building overflow fix**: Buildings no longer extend past the canvas width boundary. Building widths are clamped to remaining space, and buildings that would overflow are clipped or skipped.
- **SVG spire position fix**: Gothic/art deco spires are now correctly positioned at the top of buildings in SVG output, instead of appearing at the bottom of the canvas.
- **SVG window indexing fix**: SVG export now displays the correct interior window rows (rows 1 through h-2) instead of showing roof-level windows (row 0) as interior windows.
- **SVG building clipping**: Buildings in SVG export are now clamped to the canvas width to prevent overflow.
- **SVG city names fix**: SVG export now uses the same full list of 28 city names as the text output, ensuring consistency between the two formats.
- **Save file ANSI stripping**: The `--save` option now always writes plain text without ANSI escape codes, regardless of whether `--no-color` is set. Terminal output still respects the color setting.

## License

MIT