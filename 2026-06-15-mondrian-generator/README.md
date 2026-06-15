# 🎨 Terminal Mondrian Art Generator

Generate Piet Mondrian-style **De Stijl** compositions directly in your terminal using Unicode box-drawing characters and ANSI 24-bit true colors.

![Mondrian-style composition](https://upload.wikimedia.org/wikipedia/commons/thumb/a/ad/Piet_Mondrian_-_Composition_No._II%2C_1930.jpg/300px-Piet_Mondrian_-_Composition_No._II%2C_1930.jpg)

## What It Does

This generator recursively subdivides a rectangular canvas into smaller regions — just like Mondrian did with his iconic abstract compositions — then fills each region with one of his characteristic primary colors (red, blue, yellow) or white. Thick black borders (rendered as 2-character-wide lines using Unicode box-drawing characters `┼`, `│`, `─`, `┬`, `┴`, `├`, `┤`) separate the regions, and each composition is signed "MONDRIAN" in the bottom-right corner.

Every run produces a unique composition. Use a seed for reproducible results.

## Features

- **Recursive subdivision algorithm** — randomly splits regions horizontally or vertically, preferring the longer axis, creating authentic Mondrian-like compositions
- **24-bit ANSI true color** — uses the exact Mondrian palette: bold red (#CE2029), deep blue (#0036AA), bright yellow (#FFDE00), off-white (#F2F2F2), and black (#141414)
- **Thick black borders** — 2-character-wide borders rendered with Unicode box-drawing characters for proper intersections
- **Configurable** — control canvas size, split probability, recursion depth, minimum region size, and random seed
- **Gallery mode** — generate multiple compositions sequentially with `-n`
- **Signature watermark** — each composition is signed "MONDRIAN" in the bottom-right

## Requirements

- Python 3.6+
- A terminal that supports:
  - ANSI 24-bit true-color escape sequences
  - Unicode box-drawing characters

Most modern terminals (iTerm2, Windows Terminal, Kitty, Alacritty, GNOME Terminal) support both.

## Installation

```bash
# No dependencies needed — just copy the file!
git clone https://github.com/yourname/daily-ideas.git
cd daily-ideas/2026-06-15-mondrian-generator
chmod +x mondrian.py
```

Or just download `mondrian.py` directly.

## Usage

### Basic (fills your terminal)

```bash
python3 mondrian.py
```

### With options

```bash
# Specific size
python3 mondrian.py -W 100 -H 40

# Reproducible art with a seed
python3 mondrian.py -s 42

# More subdivisions (higher split probability)
python3 mondrian.py -p 0.95

# Fewer subdivisions (calmer composition)
python3 mondrian.py -p 0.5

# Gallery mode: generate 5 compositions
python3 mondrian.py -n 5

# Fine control over minimum region size and depth
python3 mondrian.py -m 4 -d 8
```

### All Options

| Flag | Default | Description |
|------|---------|-------------|
| `-W` / `--width` | auto-detect | Canvas width in characters |
| `-H` / `--height` | auto-detect | Canvas height in rows |
| `-s` / `--seed` | random | Random seed for reproducible art |
| `-p` / `--split-prob` | 0.85 | Probability of splitting a region (0.0–1.0) |
| `-d` / `--max-depth` | 6 | Maximum subdivision depth |
| `-m` / `--min-size` | 6 | Minimum region size before splitting stops |
| `-n` / `--count` | 1 | Number of compositions to generate |
| `--no-clear` | off | Don't clear the screen before drawing |

### As a Python Library

```python
from mondrian import generate_mondrian

# Generate art as an ANSI string
art = generate_mondrian(width=80, height=30, seed=42)
print(art)

# Custom parameters
art = generate_mondrian(
    width=100, height=40,
    seed=1337,
    split_prob=0.9,
    max_depth=7,
    min_size=4
)
print(art)
```

## How It Works

1. **Canvas initialization** — Creates a 2D grid of cells, each with a character, foreground color, and background color. The entire canvas starts as off-white.

2. **Recursive subdivision** — Starting from the full canvas (minus outer border), the algorithm:
   - Decides whether to split (based on `split_prob`, size constraints, and depth)
   - Chooses horizontal or vertical split direction (preferring the longer axis for balanced compositions)
   - Picks a random split position within valid bounds
   - Draws thick black borders at the split
   - Recursively processes each sub-region

3. **Color filling** — Leaf regions (ones that aren't split further) are filled with a random color from the Mondrian palette: red, blue, yellow, or white (white is weighted more heavily, as in real Mondrian paintings).

4. **Border intersection fixing** — A second pass identifies where horizontal and vertical borders cross and replaces the characters with the correct intersection symbols (┼, ┬, ┴, ├, ┤).

5. **Rendering** — Each cell is rendered as an ANSI-escaped string with both foreground and background 24-bit color codes, producing a seamless grid of colored rectangles separated by black lines.

## Examples

### Seed 123, 60×30
```
python3 mondrian.py -W 60 -H 30 -s 123
```
Creates a complex composition with 6+ distinct colored regions.

### Sparse, calm composition
```
python3 mondrian.py -p 0.5 -d 3 -m 10
```
Fewer splits → larger, calmer blocks of color. More like Mondrian's later, bolder works.

### Dense, busy composition
```
python3 mondrian.py -p 0.95 -d 8 -m 3
```
Many splits → a busy, mosaic-like composition. More like early Mondrian experiments.

## License

MIT