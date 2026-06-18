# 🫧 Terminal Lava Lamp v3.1.0

A mesmerizing ASCII lava lamp simulation that runs in your terminal, featuring colored wax blobs that rise and fall inside a lamp-shaped container with real-time physics, rising bubbles, heat glow effects, blob merging and splitting, screenshot export, custom theme loading, and smooth animation — all rendered with 24-bit ANSI colors and Unicode characters.

## Features

### Core Simulation
- **Realistic blob physics** — Wax blobs expand when heated (rising) and contract when cooled (sinking), with smooth velocity transitions and organic horizontal wobble
- **Blob merging** — When two blobs get close together, they merge into a larger blob (area-conserving)
- **Blob splitting** — Large blobs can spontaneously split into two smaller ones for dynamic, organic motion
- **Bubble particles** — Small rising bubbles with individual characters add visual flair and realism
- **Heat glow** — Pulsing heat source glow at the bottom that tints nearby wax
- **Lamp-shaped container** — Classic lava lamp silhouette with cap, body, and base

### Color Themes (8 themes!)
| Key | Theme  | Description                    |
|-----|--------|--------------------------------|
| `1` | Classic | Red/orange/yellow wax on dark purple |
| `2` | Ocean   | Blue/cyan/white wax on deep navy |
| `3` | Toxic   | Green/lime wax on dark forest |
| `4` | Sunset  | Pink/magenta wax on dark crimson |
| `5` | Neon    | Multi-color cycling wax on deep black |
| `6` | Aurora  | Green/purple/blue wax on dark teal |
| `7` | Ember   | Deep red/orange wax on dark brown |
| `8` | Frost   | Ice blue/white wax on dark navy |

### Interactive Controls
- **Live theme switching** — Press `1`–`8` to swap themes while running
- **Speed control** — `+`/`-` to speed up or slow down (0.25x–5.0x)
- **Pause/Resume** — Press `p` to pause with visual PAUSED indicator
- **Add blob** — Press `b` to add more wax blobs dynamically
- **Remove blob** — Press `d` to remove a random blob
- **Reset** — Press `r` to reset all blobs and bubbles
- **Screenshot** — Press `s` to save an ANSI screenshot and a plain-text version (with confirmation feedback)
- **Quit** — Press `q` or `Ctrl+C`

### Rendering
- **24-bit true color** — Smooth gradient rendering using RGB ANSI codes (no banding)
- **Glow halos** — Soft colored halos fade around wax blobs
- **Depth shading** — Interior of the lamp has subtle depth for 3D effect
- **Adaptive sizing** — Automatically fits your terminal window

### Code Quality
- **Argparse CLI** — Full `--help`, `--version`, and option flags
- **Custom theme support** — Load themes from JSON files with `--theme-file` (no longer blocked by argparse validation)
- **Input validation** — Graceful errors for invalid parameters; constructor validates speed, dimensions
- **Negative dt guard** — Simulation ignores negative or zero time deltas to prevent corruption
- **Shape width clamping** — `_shape_width()` and `_row_to_y()` clamped to prevent negative values
- **Terminal cbreak mode** — Proper raw terminal mode for single-key input (no Enter required)
- **Terminal restoration** — Terminal settings are always restored on exit, even after crashes
- **Error reporting** — Exceptions in the main loop print tracebacks instead of being silently swallowed
- **61 unit tests** — Comprehensive test suite covering all components plus bug regression tests
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
| `theme` (positional) | classic | Color theme name (built-in or custom) |
| `--theme` | classic | Color theme (alternative to positional arg; supports custom themes from `--theme-file`) |
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
| `+` / `-` | Increase / decrease speed |
| `p` | Pause / Resume |
| `b` | Add a blob |
| `d` | Remove a blob |
| `r` | Reset (new blobs and bubbles) |
| `s` | Save screenshot (with confirmation) |
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

Load with `--theme-file my_themes.json` and use with `--theme my_theme`. Each theme needs at least 4 wax colors. All color values must be in 0–255 range.

## How It Works

1. **Blob physics**: Each blob has position (x, y), velocity, and radius. Buoyancy drives blobs upward at the bottom and downward at the top, creating the classic rise-and-fall cycle. Blobs expand when rising (heated wax) and contract when sinking (cooled wax), with gentle pulsation for liveliness.

2. **Merge/split dynamics**: When two blobs are closer than `MERGE_DISTANCE` (0.08) and neither is on cooldown, they merge — the larger absorbs the smaller, conserving area. When a blob's radius exceeds `SPLIT_RADIUS_THRESHOLD` (0.10), it may randomly split into two smaller blobs, simulating a large wax mass breaking apart.

3. **Bubble particles**: Each bubble has a unique character (`·`, `∘`, `○`, `°`, `•`) assigned at creation. The renderer uses the bubble's `.char` property to display it, so different bubbles show different characters — adding visual variety.

4. **Heat glow**: The bottom of the lamp pulses with a warm glow that tints nearby wax blobs, simulating the heat source in a real lava lamp.

5. **Rendering**: For each pixel inside the lamp, the renderer calculates the combined "density" from all nearby blobs using smooth distance falloff. High-density areas get vivid wax colors and solid Unicode characters; medium areas get a soft glow; and empty areas show the dark interior with subtle depth shading.

6. **Lamp shape**: The container is defined by a parametric width function — narrow at the top cap, widening through the body, and narrowing again at the base — giving the classic lava lamp silhouette. Y-values are clamped to [0, 1] to prevent negative widths at the top.

7. **Color blending**: All colors are computed as RGB blends using 24-bit ANSI escape codes, producing smooth gradients without the banding typical of 256-color mode.

## Running Tests

```bash
python3 test_lava_lamp.py
```

The test suite (61 tests) covers blob physics, bubble behavior, lamp shape, theme switching, rendering, merge/split dynamics, screenshot export, custom theme loading, input validation, edge cases, and bug regression tests.

## Bugs Fixed in v3.1.0

- **Bubble.char unused in render**: `Bubble.__init__` assigned each bubble a random character (`self.char`) from `["·", "∘", "○", "°", "•"]`, but the render loop ignored it and used `random.choice(["·", "∘", "°"])` instead. This meant (a) each bubble's character changed every frame instead of being consistent, and (b) two of the five possible bubble characters (`○` and `•`) were never displayed. Now the render loop tracks the closest bubble and uses its `.char` property.

- **Custom themes blocked by argparse**: The `--theme` flag and positional `theme` argument used `choices=list(THEMES.keys())`, which was evaluated at module load time before `--theme-file` could be processed. This meant `python3 lava_lamp.py --theme-file custom.json --theme my_custom` would fail with "invalid choice" error. The `choices` restriction has been removed from argparse, and theme validation now happens after `--theme-file` loading via the existing manual check.

- **No screenshot save feedback**: When pressing `s` to save a screenshot, files were saved silently with no indication to the user. Now the main loop checks the return values of `Screenshot.save_ansi()` and `Screenshot.save_plain()`, and prints a confirmation message (with filenames) to stderr on success.

- **Controls line too long for default width**: The controls help line `│ [1-8]themes [+/-]speed [p]ause [b]add [d]el [r]eset [s]ave [q]uit` was 67 characters, significantly wider than the default lamp width of ~40 characters, causing it to be truncated. Shortened to `│[1-8]thm +/-spd [p]pause [b]add [d]el [r]set [s]ave [q]uit` (59 chars) to fit within typical terminal widths.

## Running Tests

```bash
python3 test_lava_lamp.py
```

## License

MIT — enjoy the mesmerizing glow!