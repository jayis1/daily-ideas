# 🫧 Terminal Lava Lamp v3.0.1

A mesmerizing ASCII lava lamp simulation that runs in your terminal, featuring colored wax blobs that rise and fall inside a lamp-shaped container with real-time physics, rising bubbles, heat glow effects, blob merging and splitting, screenshot export, custom theme loading, and smooth animation — all rendered with 24-bit ANSI colors and Unicode characters.

![Terminal Lava Lamp](https://img.shields.io/badge/terminal-lava%20lamp-purple)

## Features

### Core Simulation
- **Realistic blob physics** — Wax blobs expand when heated (rising) and contract when cooled (sinking), with smooth velocity transitions and organic horizontal wobble
- **Blob merging** — When two blobs get close together, they merge into a larger blob (area-conserving)
- **Blob splitting** — Large blobs can spontaneously split into two smaller ones for dynamic, organic motion
- **Bubble particles** — Small rising bubbles add visual flair and realism
- **Heat glow** — Pulsing heat source glow at the bottom that tints nearby wax
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
| `7` | Ember | Deep red/orange wax on dark brown |
| `8` | Frost | Ice blue/white wax on dark navy |

### Interactive Controls
- **Live theme switching** — Press `1`-`8` to swap themes while running
- **Speed control** — `+`/`-` to speed up or slow down (0.25x–5.0x)
- **Pause/Resume** — Press `p` to pause with visual PAUSED indicator
- **Add blob** — Press `b` to add more wax blobs dynamically
- **Remove blob** — Press `d` to remove a random blob
- **Reset** — Press `r` to reset all blobs and bubbles
- **Screenshot** — Press `s` to save an ANSI screenshot and a plain-text version
- **Quit** — Press `q` or `Ctrl+C`

### Rendering
- **24-bit true color** — Smooth gradient rendering using RGB ANSI codes (no banding)
- **Glow halos** — Soft colored halos fade around wax blobs
- **Depth shading** — Interior of the lamp has subtle depth for 3D effect
- **Adaptive sizing** — Automatically fits your terminal window

### Code Quality
- **Argparse CLI** — Full `--help`, `--version`, and option flags
- **Input validation** — Graceful errors for invalid parameters; constructor validates speed, dimensions
- **Negative dt guard** — Simulation ignores negative or zero time deltas to prevent corruption
- **Shape width clamping** — `_shape_width()` and `_row_to_y()` clamped to prevent negative values
- **Terminal cbreak mode** — Proper raw terminal mode for single-key input (no Enter required)
- **Terminal restoration** — Terminal settings are always restored on exit, even after crashes
- **Error reporting** — Exceptions in the main loop print tracebacks instead of being silently swallowed
- **56 unit tests** — Comprehensive test suite covering all components plus bug regression tests
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

# Load custom themes from a JSON file
python3 lava_lamp.py --theme-file my_themes.json --theme my_custom

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
| `--theme-file` | — | Load additional themes from a JSON file |
| `-W`, `--width` | auto | Terminal width (default: auto-detect) |
| `-H`, `--height` | auto | Terminal height (default: auto-detect) |
| `--blobs` | 8 | Number of wax blobs (min: 1) |
| `--bubbles` | 5 | Number of rising bubbles |
| `--speed` | 1.0 | Animation speed multiplier (must be > 0) |
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
| `d` | Remove a blob |
| `r` | Reset (new blobs and bubbles) |
| `s` | Save screenshot |
| `q` | Quit |

### Custom Theme File Format

Create a JSON file with theme definitions:

```json
{
  "my_theme": {
    "name": "My Theme",
    "bg": [10, 10, 30],
    "lamp": [40, 40, 60],
    "wax": [[255, 100, 50], [255, 150, 80], [200, 80, 40], [255, 200, 100]],
    "glow": [30, 20, 10],
    "heat": [220, 60, 20]
  }
}
```

Load with `--theme-file my_themes.json` and use with `--theme my_theme`.

## How It Works

1. **Blob physics**: Each blob has position (x, y), velocity, and radius. Buoyancy drives blobs upward at the bottom and downward at the top, creating the classic rise-and-fall cycle. Blobs expand when rising (heated wax) and contract when sinking (cooled wax), with gentle pulsation for liveliness.

2. **Merge/split dynamics**: When two blobs are closer than `MERGE_DISTANCE` (0.08) and neither is on cooldown, they merge — the larger absorbs the smaller, conserving area. When a blob's radius exceeds `SPLIT_RADIUS_THRESHOLD` (0.10), it may randomly split into two smaller blobs, simulating a large wax mass breaking apart.

3. **Bubble particles**: Small bubbles spawn near the base and float upward with a wobbling path, adding visual texture and realism.

4. **Heat glow**: The bottom of the lamp pulses with a warm glow that tints nearby wax blobs, simulating the heat source in a real lava lamp.

5. **Rendering**: For each pixel inside the lamp, the renderer calculates the combined "density" from all nearby blobs using smooth distance falloff. High-density areas get vivid wax colors and solid Unicode characters; medium areas get a soft glow; and empty areas show the dark interior with subtle depth shading.

6. **Lamp shape**: The container is defined by a parametric width function — narrow at the top cap, widening through the body, and narrowing again at the base — giving the classic lava lamp silhouette. Y-values are clamped to [0, 1] to prevent negative widths at the top.

7. **Color blending**: All colors are computed as RGB blends using 24-bit ANSI escape codes, producing smooth gradients without the banding typical of 256-color mode.

## Running Tests

```bash
python3 test_lava_lamp.py
```

The test suite (56 tests) covers blob physics, bubble behavior, lamp shape, theme switching, rendering, merge/split dynamics, screenshot export, custom theme loading, input validation, edge cases, and bug regression tests.

## Bugs Fixed in v3.0.1

- **Negative dt bug**: `LavaLamp.update()` with a negative `dt` would set `self.time` and blob `life` to negative values, corrupting the simulation. Now, `update()` ignores `dt <= 0` entirely.

- **Rendering bug at lamp top**: `_row_to_y()` returned negative y-values for rows 0 and 1, causing `_shape_width()` to return negative widths. This meant `left > right` in the render loop, resulting in no lamp content at the top rows. Both `_row_to_y()` and `_shape_width()` now clamp their values to [0, 1].

- **Non-functional keyboard controls**: The main loop used `select` + `sys.stdin.read(1)` for non-blocking input but never set the terminal to cbreak/raw mode, so keypresses required pressing Enter. Now `tty.setcbreak()` is called on startup and terminal settings are properly restored on exit.

- **Silent exception swallowing**: `except Exception: pass` in the main loop hid all errors. Now exceptions print a traceback to stderr for debugging.

- **No input validation in constructor**: `LavaLamp(speed=-1.0)`, `LavaLamp(width=2)`, or `LavaLamp(height=1)` would silently create broken instances. Now the constructor raises `ValueError` for invalid speed (≤ 0), width (< 5), and height (< 3).

- **`select` imported inside loop**: The `import select` statement was re-executed every frame. Now it's imported once at module level.

- **Inefficient `select` import in except clause**: The `except` block caught `ImportError` which was impossible since `select` was already imported inside the `try`. Now `select` is a top-level import and `ImportError` is no longer caught.

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

Speed:1.00x  Blobs:8  Time:0:42  FPS:14
│ [1-8]themes [+/-]speed [p]ause [b]add [d]el [r]eset [s]ave [q]uit
```

## What's New in v3.0.1

- **Bug fix**: Negative `dt` values no longer corrupt simulation time or blob life
- **Bug fix**: Top rows of the lamp now render correctly (was blank due to negative y-values)
- **Bug fix**: Interactive controls now work without pressing Enter (terminal cbreak mode)
- **Bug fix**: Constructor validates speed (> 0), width (≥ 5), and height (≥ 3)
- **Bug fix**: `_shape_width()` clamped to [0, 1] to prevent negative widths
- **Bug fix**: `_row_to_y()` clamped to [0, 1] to prevent negative y-values
- **Bug fix**: Main loop exceptions are reported to stderr instead of silently swallowed
- **Bug fix**: Terminal settings are properly restored on exit
- **Bug fix**: `select` module imported once at top-level instead of per-frame

## What's New in v3.0

- **2 new themes**: Ember and Frost (8 total)
- **Blob merging**: Nearby blobs merge into larger ones (area-conserving)
- **Blob splitting**: Large blobs spontaneously split into two smaller ones
- **Merge/split cooldowns**: Prevents immediate re-merge after splitting
- **Screenshot export**: Press `s` to save ANSI and plain-text screenshots
- **Custom theme loading**: `--theme-file` loads themes from JSON
- **Remove blob**: Press `d` to delete a random blob
- **FPS display**: Live FPS counter in the status bar
- **Elapsed time**: Time display in the status bar
- **Merge/split counters**: Shown in status bar when non-zero
- **Improved string building**: Uses list join instead of concatenation in render
- **Type hints**: All function signatures have type annotations

## License

MIT — enjoy the mesmerizing glow!