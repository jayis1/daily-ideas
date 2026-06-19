# Terminal Mandala Generator 🪷

A Python CLI tool that generates beautiful, radially symmetric mandala patterns in your terminal using Unicode block characters and ANSI 256-color palette.

![mandala preview](https://img.shields.io/badge/terminal-art-blue)

## Description

Terminal Mandala Generator creates intricate geometric mandala patterns with multiple layers of radial symmetry. Each mandala is built from concentric rings of different element types — circles, petals, stars, spirals, diamonds, wheels, wave rings, and more — all reflected with rotational symmetry to produce the classic mandala form.

The generator uses Unicode characters (●, ◆, ✦, ⬡, ◎, etc.) and ANSI 256-color codes to render rich, colorful patterns directly in the terminal. Characters are plotted using polar coordinates with aspect-ratio correction so the mandalas appear circular even in non-square terminal cells.

## Features

- **10 element types**: circles, dotted circles, petals, stars, wheels, spiral arms, diamonds, fractal rings, wave rings, and filled rings
- **5 color palettes**: warm, cool, earth, neon, and fire
- **Configurable complexity**: 3–8 layers per mandala
- **Reproducible output**: use `--seed` to regenerate the same mandala
- **Batch generation**: create multiple mandalas at once with `--batch`
- **Save to file**: export mandalas as text files
- **ANSI color support**: full 256-color terminal rendering with configurable background
- **No-color mode**: for terminals without color support or for plain text export
- **Radial symmetry**: all elements are drawn with rotational symmetry for authentic mandala aesthetics

## Installation

No external dependencies required — uses only Python 3 standard library.

```bash
# Clone the repo or just download mandala.py
git clone <repo-url>
cd 2026-06-19-terminal-mandala-generator

# Make executable (optional)
chmod +x mandala.py
```

## How to Run

```bash
# Generate a random mandala
python3 mandala.py

# With specific seed for reproducibility
python3 mandala.py --seed 42

# Choose a color palette
python3 mandala.py --palette neon

# Set complexity (number of layers, 3-8)
python3 mandala.py --complexity 6

# Custom size
python3 mandala.py --width 120 --height 60

# Dark background with custom color
python3 mandala.py --bg 235

# Save to file
python3 mandala.py --seed 42 --save my_mandala.txt

# Generate 5 different mandalas in batch
python3 mandala.py --batch 5 --seed 100 --save mandala.txt

# No-color mode (plain ASCII output)
python3 mandala.py --no-color --seed 42

# Run tests
python3 test_mandala.py
```

## Usage Examples

### Quick mandala with fire palette
```bash
python3 mandala.py --palette fire --complexity 5
```

### Earth-toned mandala saved to file
```bash
python3 mandala.py --palette earth --seed 777 --save earth_mandala.txt
```

### Batch generate 10 mandalas
```bash
python3 mandala.py --batch 10 --seed 42 --palette cool --save output/mandala.txt
```

### Plain text mandala (no ANSI colors)
```bash
python3 mandala.py --no-color --complexity 4 --seed 123
```

## How It Works

1. A canvas grid is created with configurable width and height
2. A random seed initializes the random number generator for reproducibility
3. Multiple mandala elements are layered from center outward:
   - Each element type uses polar coordinates with aspect-ratio correction
   - Elements are drawn with rotational symmetry (4, 6, 8, 10, 12, or 16-fold)
4. Characters and colors are selected from curated Unicode and ANSI palettes
5. The final canvas is rendered with ANSI escape codes for terminal display

### Element Types

| Element | Description |
|---------|-------------|
| `circle` | Continuous circle of characters at a given radius |
| `ring` | Dotted circle with evenly-spaced characters |
| `petals` | Leaf/petal shapes radiating from center |
| `dots` | Decorative dot patterns in a ring |
| `star` | Star polygon connecting inner and outer radii |
| `wheel` | Spoke lines radiating from center |
| `spiral` | Spiral arms winding outward from center |
| `diamonds` | Diamond shapes arranged in a ring |
| `fractal_ring` | Ring with sub-rings at each node |
| `wave_ring` | Sinusoidal wavy ring pattern |