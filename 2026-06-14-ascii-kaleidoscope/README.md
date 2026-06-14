# ✦ ASCII Kaleidoscope

A mesmerizing terminal-based kaleidoscope that generates real-time, animated, symmetric patterns using Unicode block characters and ANSI 256-color mode. The engine computes patterns in a single triangular wedge and mirrors them across multiple axes of symmetry — just like a real kaleidoscope!

![kaleidoscope](https://img.shields.io/badge/type-visualization-purple) ![python](https://img.shields.io/badge/python-3.7+-blue) ![terminal](https://img.shields.io/badge/output-ANSI%20256-green) ![version](https://img.shields.io/badge/version-1.2.0-orange)

## Features

- **8 unique pattern modes**: spiral, ripple, crystal, flower, mandala, wave, plasma, vortex
- **Configurable symmetry**: 4 to 24 segments of kaleidoscopic mirroring
- **Smooth animation**: Half-block Unicode characters (▀/▄) give each terminal row 2 virtual pixels for higher visual fidelity
- **Enhanced color palette**: Saturation-adjusted ANSI 256-color mapping with full 6×6×6 cube coverage and smoother transitions
- **FPS counter**: Live frame rate display in the info bar
- **Deterministic seeds**: Use `--seed` to reproduce the exact same pattern session
- **Clean fullscreen mode**: `--no-info` hides the info bar for distraction-free viewing
- **Live controls**: Change pattern, speed, and segments without restarting
- **Escape sequence handling**: Arrow keys and other escape sequences are properly consumed (won't trigger unintended actions)
- **Correct vertical positioning**: Display starts at row 1 with no offset
- **Paused-state FPS**: FPS counter only tracks rendered frames (not spin-loop iterations)
- **Zero dependencies**: Pure Python standard library — no installs needed

## How It Works

1. Each frame, the viewport is treated as a circular region in polar coordinates.
2. The angle `θ` is folded into a single "wedge" segment (e.g., for 8-fold symmetry, each wedge spans 45°).
3. Every other wedge is mirror-reflected, creating perfect kaleidoscopic symmetry.
4. The pattern function combines multiple sinusoidal waves in `r` and `θ` with time-varying phases.
5. Upper/lower half-block characters (▀/▄) encode two vertical sub-pixels per terminal row, with foreground and background colors set independently for sub-pixel color depth.
6. The color palette slowly shifts over time, producing hypnotic hue cycling.
7. Pixels outside the circular viewport are rendered as dark space using ANSI color 16 (true black), creating a clean disc boundary.

## Installation

No installation required — just Python 3.7+:

```bash
# Clone or download, then:
cd 2026-06-14-ascii-kaleidoscope
```

## How to Run

```bash
# Default: random pattern, 8 segments
python3 kaleidoscope.py

# Choose a specific pattern
python3 kaleidoscope.py --pattern spiral
python3 kaleidoscope.py --pattern crystal
python3 kaleidoscope.py --pattern plasma

# More segments = more mirrors
python3 kaleidoscope.py --segments 12

# Slow it down or speed it up
python3 kaleidoscope.py --speed 0.5
python3 kaleidoscope.py --speed 3.0

# Reproduce a specific pattern with a seed
python3 kaleidoscope.py --seed 42

# Clean fullscreen (no info bar)
python3 kaleidoscope.py --no-info

# Combine options
python3 kaleidoscope.py -p mandala -s 16 --speed 1.5 --seed 12345

# Show version
python3 kaleidoscope.py --version

# Show help
python3 kaleidoscope.py --help
```

### Available Patterns

| Pattern   | Description                                           |
|-----------|-------------------------------------------------------|
| `spiral`  | Classic swirling spirals with multi-frequency arms     |
| `ripple`  | Concentric wave ripples radiating outward              |
| `crystal` | Geometric crystal-like facets and shards               |
| `flower`  | Organic petal-like forms that bloom and shift           |
| `mandala` | Sacred-geometry style with rings and spokes            |
| `wave`    | Ocean-inspired wave interference patterns               |
| `plasma`  | Classic plasma effect with vivid color cycling         |
| `vortex`  | Spinning vortex with depth illusion                    |

### Interactive Controls (while running)

| Key       | Action                     |
|-----------|----------------------------|
| `q`       | Quit                       |
| `r`       | Randomize pattern          |
| `space`   | Pause / resume             |
| `+` / `=` | Increase speed              |
| `-` / `_` | Decrease speed              |
| `]`       | Increase segments           |
| `[`       | Decrease segments           |

Arrow keys and other escape sequences are safely consumed and will not trigger unintended actions.

## Usage Examples

```bash
# Quick meditative moment
python3 kaleidoscope.py -p mandala --speed 0.5

# High-energy visual
python3 kaleidoscope.py -p crystal -s 12 --speed 3.0

# Reproduce a favorite pattern
python3 kaleidoscope.py -p vortex --seed 777

# Clean fullscreen display
python3 kaleidoscope.py --no-info

# Simple and soothing
python3 kaleidoscope.py -p ripple --segments 6
```

## Testing

```bash
python3 -m unittest test_kaleidoscope -v
```

Runs 35 unit tests covering:
- All 8 patterns render correctly
- Segment count normalization (odd → even, min 4) via property setter
- Speed clamping (0.2–5.0)
- Deterministic output with `--seed`
- Animation continuity across frames
- Palette generation correctness and full color range
- Degenerate, zero, and negative viewport sizes
- Pattern fallback for unknown names
- Outside-circle pixel colors use correct bg_dark value
- Output character validity (space, ▀, ▄ only)
- ANSI helper function correctness

## Changelog

### v1.2.0 — Bug fixes

- **Fixed vertical offset bug**: The display was shifted down by 1 row because a `\n` was inserted between the initial cursor positioning (`move_cursor(1,1)`) and the first row of output. Now each row uses its own `move_cursor` call for correct positioning.
- **Fixed escape sequence handling**: Arrow keys send `\x1b[` followed by `A`/`B`/`C`/`D`. Previously, the `[` character was read individually and triggered unintended segment decreases. `get_key_nonblock()` now properly consumes CSI and SS3 escape sequences.
- **Fixed color truncation in `generate_palette`**: The palette used `* 5` (integer truncation) to map continuous values to the 0–5 channel range, which underrepresented bright colors — only 1 out of 256 entries reached the maximum channel value. Changed to `* 5.999` with clamping, now 69 entries reach max value for full color range.
- **Fixed exit cursor position**: On exit, the cursor was placed at `rows + info_rows + 1`, causing the terminal to scroll. Fixed to `rows + info_rows` for clean exit positioning.
- **Fixed FPS counter inflation when paused**: `fps_frame_count` was incremented every loop iteration regardless of whether a frame was actually rendered. When paused, the tight loop ran thousands of iterations per second, producing wildly inflated FPS readings. Now only rendered frames are counted.
- **Fixed outside-circle background color**: Pixels outside the kaleidoscope disc used `bg=0` (system color 0, which may not be black on all terminals) instead of `bg_dark=16` (ANSI color 16 = true `#000000`). Both fg and bg now correctly use `bg_dark (16)` for outside-circle pixels.
- **Added `segments` property**: Direct assignment of odd or too-small values to `ks.segments` now normalizes automatically (even, min 4), preventing potential rendering issues from live segment adjustments.
- **Removed unused import**: `namedtuple` from `collections` was imported but never used.

## What It Does

The ASCII Kaleidoscope transforms your terminal into a mesmerizing light show. It mathematically generates wave interference patterns in polar coordinates, folds them through kaleidoscopic symmetry, and renders the result as a smoothly animated, color-cycling display. Each session is unique thanks to randomized frequency and phase parameters (unless you specify a seed). It's both a visual toy and a demonstration of how simple trigonometric functions, when composed and reflected through symmetry, can produce stunningly complex and beautiful results.