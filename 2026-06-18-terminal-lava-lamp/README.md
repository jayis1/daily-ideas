# 🫧 Terminal Lava Lamp v3.0

A mesmerizing ASCII lava lamp simulation that runs in your terminal, featuring colored wax blobs that rise and fall inside a lamp-shaped container with real-time physics, blob merging/splitting, rising bubbles, heat glow effects, screenshot export, and smooth animation — all rendered with 24-bit ANSI colors and Unicode characters.

![Terminal Lava Lamp](https://img.shields.io/badge/terminal-lava%20lamp-purple)

## Features

### Core Simulation
- **Realistic blob physics** — Wax blobs expand when heated (rising) and contract when cooled (sinking), with smooth velocity transitions and organic horizontal wobble
- **Blob merging** — When two blobs drift close together, they merge into one larger blob (area-conserving), creating the satisfying "joining" effect of a real lava lamp
- **Blob splitting** — Large blobs spontaneously break apart into two smaller blobs, simulating a wax mass breaking up
- **Merge & split counters** — Track how many merges and splits have occurred in the status bar
- **Bubble particles** — Small rising bubbles add visual flair and realism to the simulation
- **Heat glow** — A pulsing heat source glow at the bottom of the lamp that tints nearby wax
- **Lamp-shaped container** — Classic lava lamp silhouette with cap, body, and base

### Color Themes (8 themes!)
| Key | Theme | Description |
|-----|-------|-------------|
| `1` | Classic | Red/orange/yellow wax on dark purple |
| `2` | Ocean | Blue/cyan/white wax on deep navy |
| `3` | Toxic | Green/lime wax on dark forest |
| `4` | Sunset | Pink/magenta wax on dark crimson |
| `5` | Neon | Multi-color cycling wax on deep black |
| `6` | Aurora | Green/purple/blue wax on dark teal |
| `7` | **Ember** 🆕 | Deep red/orange/fire wax on dark charcoal |
| `8` | **Frost** 🆕 | Ice blue/white wax on midnight blue |

### Interactive Controls
- **Live theme switching** — Press `1`–`8` to swap themes while running
- **Speed control** — `+`/`-` to speed up or slow down (0.25x–5.0x)
- **Pause/Resume** — Press `p` to pause with visual PAUSED indicator
- **Add blobs** — Press `b` to add more wax blobs dynamically
- **Remove blobs** 🆕 — Press `d` to remove a random blob
- **Reset** — Press `r` to reset all blobs and bubbles (also resets merge/split counters)
- **Screenshot** 🆕 — Press `s` to save the current frame as both ANSI and plain text files
- **Quit** — Press `q` or `Ctrl+C`

### Rendering
- **24-bit true color** — Smooth gradient rendering using RGB ANSI codes (no banding)
- **Glow halos** — Soft colored halos fade around wax blobs
- **Depth shading** — Interior of the lamp has subtle depth for 3D effect
- **Adaptive sizing** — Automatically fits your terminal window
- **FPS counter** 🆕 — Real-time FPS display in the status bar
- **Elapsed timer** 🆕 — Shows how long the lamp has been running

### Custom Themes 🆕
- **`--theme-file`** — Load your own color themes from a JSON file
- Themes are defined as JSON with `name`, `bg`, `lamp`, `wax` (4+ colors), `glow`, and `heat` fields
- Colors are `[R, G, B]` arrays (0–255)
- Custom themes merge with built-in themes and are available immediately

### Code Quality
- **Argparse CLI** — Full `--help`, `--version`, and option flags
- **Input validation** — Graceful errors for invalid parameters
- **46 unit tests** — Comprehensive test suite covering all components including merge/split, screenshots, theme loading, and edge cases
- **Type hints** — Function signatures use Python type hints
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

# Frost theme with larger size
python3 lava_lamp.py frost -W 60 -H 40

# Load custom themes from a JSON file
python3 lava_lamp.py --theme-file my_themes.json --theme custom1

# Show version
python3 lava_lamp.py --version

# Show help (all options)
python3 lava_lamp.py --help
```

### Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `theme` (positional) | classic | Color theme: classic, ocean, toxic, sunset, neon, aurora, ember, frost |
| `--theme` | classic | Color theme (alternative to positional) |
| `--theme-file` | — | Load additional themes from a JSON file 🆕 |
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
| `1`–`8` | Switch theme |
| `+` / `=` | Increase speed |
| `-` / `_` | Decrease speed |
| `p` | Pause / Resume |
| `b` | Add a blob |
| `d` | Remove a random blob 🆕 |
| `r` | Reset (new blobs and bubbles) |
| `s` | Save screenshot 🆕 |
| `q` | Quit |

### Custom Theme File Format 🆕

Create a JSON file like this:

```json
{
  "my_custom": {
    "name": "My Custom Theme",
    "bg": [10, 10, 30],
    "lamp": [40, 30, 60],
    "wax": [
      [255, 100, 200],
      [200, 50, 255],
      [100, 200, 255],
      [255, 255, 100],
      [50, 255, 150],
      [255, 50, 100]
    ],
    "glow": [30, 15, 40],
    "heat": [200, 50, 150]
  }
}
```

Then run: `python3 lava_lamp.py --theme-file my_themes.json --theme my_custom`

## How It Works

1. **Blob physics**: Each blob has position (x, y), velocity, and radius. Buoyancy drives blobs upward at the bottom and downward at the top, creating the classic rise-and-fall cycle. Blobs expand when rising (heated wax) and contract when sinking (cooled wax), with gentle pulsation for liveliness.

2. **Blob merging** 🆕: When two blobs come within a threshold distance (`MERGE_DISTANCE = 0.08`) and neither is on merge cooldown, they merge. The resulting blob conserves total area (πr₁² + πr₂² = πr_new²) and averages their velocities. A cooldown period prevents immediate re-merging.

3. **Blob splitting** 🆕: When a blob grows larger than `SPLIT_RADIUS_THRESHOLD = 0.10` and isn't on split cooldown, it has a small random chance each frame to split into two daughter blobs. Each daughter has radius r/√2 (area-conserving), offset positions, and a merge cooldown so they don't immediately re-merge.

4. **Bubble particles**: Small bubbles spawn near the base and float upward with a wobbling path, adding visual texture and realism.

5. **Heat glow**: The bottom of the lamp pulses with a warm glow that tints nearby wax blobs, simulating the heat source in a real lava lamp.

6. **Rendering**: For each pixel inside the lamp, the renderer calculates the combined "density" from all nearby blobs using smooth distance falloff. High-density areas get vivid wax colors and solid Unicode characters; medium areas get a soft glow; and empty areas show the dark interior with subtle depth shading.

7. **Lamp shape**: The container is defined by a parametric width function — narrow at the top cap, widening through the body, and narrowing again at the base — giving the classic lava lamp silhouette.

8. **Color blending**: All colors are computed as RGB blends using 24-bit ANSI escape codes, producing smooth gradients without the banding typical of 256-color mode.

## Running Tests

```bash
python3 test_lava_lamp.py
```

The test suite (46 tests) covers blob physics, bubble behavior, lamp shape, theme switching, rendering, input validation, merge/split dynamics, screenshot export, custom theme loading, edge cases, and more.

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
Speed:1.00x  Blobs:7  Time:0:42  FPS:15  Merges:3  Splits:1
│ [1-8]themes [+/-]speed [p]ause [b]add [d]el [r]eset [s]ave [q]uit
```

## What's New in v3.0

- **Blob merging**: Nearby blobs merge into one larger blob (area-conserving), creating realistic lava lamp dynamics
- **Blob splitting**: Large blobs can spontaneously split apart, simulating wax masses breaking up
- **2 new themes**: Ember (deep fire colors) and Frost (icy blues/whites) — 8 total
- **Remove blob**: Press `d` to remove a random blob
- **Screenshot export**: Press `s` to save the current frame as ANSI (.txt) and plain text files
- **Custom theme files**: `--theme-file` flag loads user themes from JSON
- **FPS counter**: Real-time FPS display in the status bar
- **Elapsed timer**: Shows minutes:seconds of runtime
- **Merge/split counters**: Track blob dynamics in the status bar
- **`strip_ansi()` utility**: For screenshot plain text export
- **Type hints**: Full type annotations on function signatures
- **46 unit tests**: 18 new tests covering merge/split, screenshots, theme loading, new themes, and cooldowns

## License

MIT — enjoy the mesmerizing glow!