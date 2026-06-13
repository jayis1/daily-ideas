# 🔮 ASCII Fractal Explorer

Explore Mandelbrot and Julia sets directly in your terminal — with interactive zoom, pan, palette switching, and smooth coloring. Zero external dependencies.

![Fractal](https://img.shields.io/badge/type-visualization-blue) ![Python](https://img.shields.io/badge/python-3.8+-green) ![CLI](https://img.shields.io/badge/interface-curses%20%2B%20CLI-orange) ![Version](https://img.shields.io/badge/version-1.0.0-blue)

## What It Does

This is a real-time fractal viewer that renders Mandelbrot and Julia sets as ASCII art in your terminal. You can zoom into the infinite detail of the Mandelbrot set, switch to Julia set mode with 8 built-in presets, cycle through 6 color palettes, and export high-resolution renders to text files.

The fractal is computed per-pixel using escape-time iteration, with optional smooth coloring (using the renormalization trick with log₂(log₂(|z|))) for silky gradient transitions instead of harsh color bands.

## Features

- **Interactive curses UI** — Arrow keys to pan, +/- to zoom, all in real time
- **Mandelbrot & Julia sets** — Toggle between fractal types with `M`
- **8 Julia presets** — Cycle through famous Julia set parameters with `J`
- **6 color palettes** — Fire, Ocean, Matrix, Electric, Earth, Grayscale
- **Smooth coloring** — Continuous iteration count for beautiful gradients (toggle with `S`)
- **Auto-scaling iterations** — Max iterations increase automatically as you zoom deeper
- **Export to file** — Save high-resolution renders with ANSI 24-bit color or plain ASCII
- **Non-interactive mode** — Generate fractals from the command line for scripts and pipelines
- **Zero dependencies** — Pure Python 3.8+ standard library only

## Installation

No installation needed — just download and run:

```bash
# Clone or download fractal_explorer.py
curl -O https://raw.githubusercontent.com/.../fractal_explorer.py
```

Or copy the file from this directory.

## How to Run

### Interactive mode (requires a terminal)

```bash
python3 fractal_explorer.py
```

### Export to file

```bash
# Mandelbrot set, fire palette, 200x80 resolution
python3 fractal_explorer.py --export mandelbrot.txt --width 200 --height 80 --iter 150

# Zoom into seahorse valley with ocean palette
python3 fractal_explorer.py --export seahorse.txt --center="-0.745,0.186" --zoom=0.005 --palette ocean --iter 300

# Julia set, plain text (no ANSI colors)
python3 fractal_explorer.py --julia --julia-c="-0.7,0.27015" --plain --width 100 --height 50 --export julia.txt
```

### Print directly to terminal (no curses)

```bash
# Quick render in terminal (no TUI)
python3 fractal_explorer.py --no-curses --plain --width 80 --height 30

# With ANSI colors
python3 fractal_explorer.py --no-curses --width 80 --height 30
```

## Interactive Controls

| Key | Action |
|---|---|
| Arrow keys | Pan around the fractal |
| `+` / `-` | Zoom in / out |
| `M` | Toggle Mandelbrot / Julia mode |
| `J` | Cycle through Julia set presets |
| `P` | Cycle color palette |
| `I` / `Shift+I` | Increase / decrease max iterations |
| `S` | Toggle smooth coloring |
| `R` | Reset view to default |
| `E` | Export current view to `~/fractal_export.txt` |
| `H` | Show help overlay |
| `Q` / `Esc` | Quit |

## Usage Examples

### Deep zoom into the Mandelbrot set
```bash
python3 fractal_explorer.py --center="-0.743643,0.131826" --zoom=0.0001 --iter 500
```

### Electric Julia set
```bash
python3 fractal_explorer.py --julia --julia-c="-0.8,0.156" --palette electric
```

### Matrix-style Mandelbrot export
```bash
python3 fractal_explorer.py --palette matrix --plain --export matrix_mandelbrot.txt --width 150 --height 60
```

### Earth-toned Julia set at full zoom
```bash
python3 fractal_explorer.py --julia --julia-c="0.285,0.01" --palette earth --zoom=0.005 --export julia_earth.txt --width 200 --height 100
```

## How It Works

The renderer computes escape-time iteration for each pixel position in the complex plane. For each point (cx, cy):

1. Start with z = 0 (Mandelbrot) or z = (cx, cy) (Julia)
2. Iterate z = z² + c until |z| > 2 or max iterations is reached
3. Map the iteration count to a character + color from the active palette

**Smooth coloring** uses the renormalization formula to get a continuous iteration count:

```
smooth_iter = n + 1 - log₂(log₂(|z|))
```

This eliminates the harsh banding between iteration levels and produces gradients that look like continuous color fields.

The terminal character aspect ratio (≈0.5) is factored in so the fractal doesn't appear stretched.

## Project Structure

```
fractal_explorer/
├── README.md              ← You are here
└── fractal_explorer.py    ← Everything in one file
```

## Requirements

- Python 3.8+
- Terminal with color support (for interactive mode)
- No external packages needed

---

*Part of the [Daily Ideas](https://github.com/…) collection — AI-generated projects, one at a time.*