# LOOM — Terminal Generative Art Weaver

LOOM is a terminal-based generative art tool that creates animated geometric tapestry patterns using Unicode block characters. It simulates a textile loom, layering trigonometric wave functions to produce evolving, woven-look patterns directly in your terminal with full 24-bit color support.

## Features

- **6 weave patterns**: plain, twill, satin, herringbone, basket, diamond — each modeled after real textile weave structures
- **7 color palettes**: sunset, ocean, forest, neon, ember, aurora, monochrome
- **Animated output**: continuously evolving patterns that flow and shift like a real loom in motion
- **Unicode block characters**: uses ░▒▓█▀▄▌▐▘▝▖▗ and more for fine-grained texture
- **Layered wave synthesis**: multiple sine/cosine layers with warp/weft thread modulation create complex interference patterns
- **Reproducible seeds**: use `--seed` to recreate the exact same pattern
- **ASCII fallback mode**: `--ascii` for terminals without color support
- **Snapshot mode**: output a single frame for piping to files
- **Save-to-file mode**: export multiple frames as a text file

## How It Works

LOOM generates patterns by layering multiple trigonometric functions, similar to how real fabric is woven from interlocking warp and weft threads. Each pixel's value is computed from:

1. **Weave layers** — sine and cosine waves with unique frequencies, phases, and speeds
2. **Warp/weft modulation** — per-column and per-row thread parameters that mimic real fabric structure  
3. **Global drift** — a slow-evolving phase offset that makes the entire tapestry shift over time

The resulting value is mapped to both a Unicode character (chosen by the weave pattern algorithm) and a color (interpolated through the selected palette), producing a richly textured, continuously evolving textile visualization.

## Installation

No dependencies beyond Python 3.6+:

```bash
# Just download and run
chmod +x loom.py
```

## How to Run

### Live Animation

```bash
# Default animation (sunset palette, twill pattern)
python3 loom.py

# Neon colors with diamond weave
python3 loom.py --palette neon --pattern diamond

# Reproducible pattern with 5 layers of complexity
python3 loom.py --seed 42 --layers 5

# ASCII-only mode (works in any terminal)
python3 loom.py --ascii

# Ocean palette, herringbone pattern, custom size
python3 loom.py --palette ocean --pattern herringbone --width 100 --height 35

# Run for exactly 30 seconds
python3 loom.py --duration 30
```

Press `Ctrl+C` to stop the animation.

### Single Snapshot

```bash
# Print one frame (useful for piping to files)
python3 loom.py --snapshot --ascii > art.txt

# Snapshot with colors (view in terminal)
python3 loom.py --snapshot
```

### Save Frames to File

```bash
# Save 10 frames to a text file
python3 loom.py --save output.txt --save-frames 10

# Save 30 frames with custom interval
python3 loom.py --save animation.txt --save-frames 30
```

## Usage Examples

| Command | Effect |
|---|---|
| `python3 loom.py` | Default animated tapestry |
| `python3 loom.py -p aurora --pattern diamond` | Aurora-colored diamond weave |
| `python3 loom.py -p ember --pattern herringbone -l 4` | Ember herringbone, 4 layers |
| `python3 loom.py --seed 1337 --snapshot --ascii` | Reproducible single-frame ASCII art |
| `python3 loom.py --ascii --fps 10 --width 80` | 80-wide ASCII animation at 10fps |
| `python3 loom.py --pattern satin -p neon` | Neon satin weave pattern |

## What It Does

LOOM transforms your terminal into a generative art canvas that mimics real textile weaving. Each frame, it computes a complex interference pattern from layered mathematical waves, then maps those values to Unicode block characters arranged in traditional weave structures (twill diagonals, herringbone Vs, satin floats, etc.) and smoothly interpolated colors from the chosen palette.

The result is a mesmerizing, continuously evolving tapestry that looks like fabric being woven in real time — but is entirely mathematical, created from the interference of sine waves and the structure of weave algorithms.