# 🫧 Terminal Lava Lamp v2.0

A mesmerizing ASCII lava lamp simulation that runs in your terminal, featuring colored wax blobs that rise and fall inside a lamp-shaped container with real-time physics, rising bubbles, heat glow effects, and smooth animation — all rendered with 24-bit ANSI colors and Unicode characters.

![Terminal Lava Lamp](https://img.shields.io/badge/terminal-lava%20lamp-purple)

## Features

### Core Simulation
- **Realistic blob physics** — Wax blobs expand when heated (rising) and contract when cooled (sinking), with smooth velocity transitions and organic horizontal wobble
- **Bubble particles** — Small rising bubbles add visual flair and realism to the simulation
- **Heat glow** — A pulsing heat source glow at the bottom of the lamp that tints nearby wax
- **Lamp-shaped container** — Classic lava lamp silhouette with cap, body, and base

### Color Themes (6 themes!)
| Key | Theme | Description |
|-----|-------|-------------|
| `1` | Classic | Red/orange/yellow wax on dark purple |
| `2` | Ocean | Blue/cyan/white wax on deep navy |
| `3` | Toxic | Green/lime wax on dark forest |
| `4` | Sunset | Pink/magenta wax on dark crimson |
| `5` | Neon | Multi-color cycling wax on deep black |
| `6` | Aurora | Green/purple/blue wax on dark teal |

### Interactive Controls
- **Live theme switching** — Press `1`-`6` to swap themes while running
- **Speed control** — `+`/`-` to speed up or slow down (0.25x–5.0x)
- **Pause/Resume** — Press `p` to pause with visual PAUSED indicator
- **Add blobs** — Press `b` to add more wax blobs dynamically
- **Reset** — Press `r` to reset all blobs and bubbles
- **Quit** — Press `q` or `Ctrl+C`

### Rendering
- **24-bit true color** — Smooth gradient rendering using RGB ANSI codes (no banding)
- **Glow halos** — Soft colored halos fade around wax blobs
- **Depth shading** — Interior of the lamp has subtle depth for 3D effect
- **Adaptive sizing** — Automatically fits your terminal window

### Code Quality
- **Argparse CLI** — Full `--help`, `--version`, and option flags
- **Input validation** — Graceful errors for invalid parameters
- **28 unit tests** — Comprehensive test suite covering all components
- **Well-documented** — Every class and method has docstrings

## Installation

No dependencies required — uses only the Python standard library!

```bash
cd ~/daily-ideas/2026-06-18-terminal-lava-lamp
```

Or just copy `lava_lamp.py` — it's a single self-contained file.

**Requires a terminal that supports 24-bit (true-color) ANSI codes** — most modern terminals (iTerm2, Windows Terminal, kitty, Alacritty, GNOME Terminal) support this.

## Usage

### Basic (default Classic theme)
```bash
python3 lava_lamp.py
```

### With options
```bash
# Ocean theme
python3 lava_lamp.py ocean
python3 lava_lamp.py --theme ocean

# Double speed with more blobs
python3 lava_lamp.py --speed 2 --blobs 12

# Neon theme with larger size
python3 lava_lamp.py neon -W 60 -H 40

# Show version
python3 lava_lamp.py --version

# Show help (all options)
python3 lava_lamp.py --help
```

### Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `theme` (positional) | classic | Color theme: classic, ocean, toxic, sunset, neon, aurora |
| `--theme` | classic | Color theme (alternative to positional) |
| `-W`, `--width` | auto | Terminal width (default: auto-detect) |
| `-H`, `--height` | auto | Terminal height (default: auto-detect) |
| `--blobs` | 8 | Number of wax blobs (min: 1) |
| `--bubbles` | 5 | Number of rising bubbles |
| `--speed` | 1.0 | Animation speed multiplier (0.25–5.0) |
| `--fps` | 15 | Target frames per second (1–60) |
| `--version` | — | Show version and exit |

### Interactive Controls (while running)

| Key | Action |
|-----|--------|
| `1`–`6` | Switch theme |
| `+` / `=` | Increase speed |
| `-` / `_` | Decrease speed |
| `p` | Pause / Resume |
| `b` | Add a blob |
| `r` | Reset (new blobs and bubbles) |
| `q` | Quit |

## How It Works

1. **Blob physics**: Each blob has position (x, y), velocity, and radius. Buoyancy drives blobs upward at the bottom and downward at the top, creating the classic rise-and-fall cycle. Blobs expand when rising (heated wax) and contract when sinking (cooled wax), with gentle pulsation for liveliness.

2. **Bubble particles**: Small bubbles spawn near the base and float upward with a wobbling path, adding visual texture and realism.

3. **Heat glow**: The bottom of the lamp pulses with a warm glow that tints nearby wax blobs, simulating the heat source in a real lava lamp.

4. **Rendering**: For each pixel inside the lamp, the renderer calculates the combined "density" from all nearby blobs using smooth distance falloff. High-density areas get vivid wax colors and solid Unicode characters; medium areas get a soft glow; and empty areas show the dark interior with subtle depth shading.

5. **Lamp shape**: The container is defined by a parametric width function — narrow at the top cap, widening through the body, and narrowing again at the base — giving the classic lava lamp silhouette.

6. **Color blending**: All colors are computed as RGB blends using 24-bit ANSI escape codes, producing smooth gradients without the banding typical of 256-color mode.

## Running Tests

```bash
python3 test_lava_lamp.py
```

The test suite (28 tests) covers blob physics, bubble behavior, lamp shape, theme switching, rendering, input validation, edge cases, and more.

## Example Output

```
  ✦ CLASSIC LAVA LAMP ✦

         ▄▄▄▄▄▄▄▄▄▄▄
      │  ░░░████████░░░  │
      │  ░░██████████░░  │
      │     ░░████░░     │
      │        ░░        │
      │  ░░░████████░░░  │
      │  ██████████████  │
      │  ██████████████  │
         ▀▀▀▀▀▀▀▀▀▀▀

Speed:1.0x  Blobs:8  │ [1-6]themes [+/-]speed [p]ause [b]lob [r]eset [q]uit
```

## What's New in v2.0

- **2 new themes**: Neon and Aurora (6 total)
- **Bubble particles** for visual flair and realism
- **Heat glow effect** at the bottom of the lamp with pulsing
- **Argparse CLI** with `--help`, `--version`, `--speed`, `--blobs`, `--bubbles`, `--fps`, `-W`, `-H`
- **Interactive speed control** (`+`/`-` keys, 0.25x–5.0x range)
- **Pause/Resume** with visual indicator
- **Add blobs** dynamically with `b` key
- **Reset** simulation with `r` key
- **RGB clamping** in color conversion to prevent out-of-range values
- **`dt` capping** to prevent physics explosions on large time steps
- **Comprehensive error handling** with graceful fallbacks
- **28 unit tests** covering all components
- **Full docstrings** on every class and method

## License

MIT — enjoy the mesmerizing glow!