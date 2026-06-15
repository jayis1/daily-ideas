# 🎨 Terminal Mondrian Art Generator v2.0

Generate Piet Mondrian-style **De Stijl** compositions directly in your terminal using Unicode box-drawing characters and ANSI 24-bit true colors.

Every run produces a unique composition. Use a seed for reproducible results.

## Features

- **Recursive subdivision algorithm** — randomly splits regions horizontally or vertically, preferring the longer axis, creating authentic Mondrian-like compositions
- **5 color palettes** — classic Mondrian, neon, pastel, 70s retro, and dark mode
- **24-bit ANSI true color** — vivid, accurate color rendering
- **Thick black borders** — 2-character-wide borders rendered with Unicode box-drawing characters (┼, │, ─, ┬, ┴, ├, ┤)
- **Animation mode** — watch the composition being drawn row by row
- **SVG export** — save compositions as scalable vector graphics
- **HTML export** — save compositions as standalone web pages
- **Composition statistics** — see color distribution and region counts
- **Configurable** — control canvas size, split probability, recursion depth, minimum region size, and random seed
- **Gallery mode** — generate multiple compositions sequentially with `-n`
- **Signature watermark** — each composition is signed "MONDRIAN" (opt-out with `--no-signature`)
- **`--version` and `--help`** — standard CLI flags

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

### Choose a palette

```bash
# Neon colors
python3 mondrian.py -p neon

# Pastel colors
python3 mondrian.py -p pastel

# Dark mode
python3 mondrian.py -p dark

# 70s retro
python3 mondrian.py -p seventies
```

### Reproducible art with a seed

```bash
python3 mondrian.py -s 42
```

### Animation mode

Watch the composition being drawn progressively:

```bash
python3 mondrian.py --animate
python3 mondrian.py --animate --delay 0.05   # slower animation
```

### Export to SVG or HTML

```bash
# Export as SVG
python3 mondrian.py --export svg -o composition.svg

# Export as HTML
python3 mondrian.py --export html -o composition.html

# Specify size and seed for reproducible exports
python3 mondrian.py -W 100 -H 50 -s 42 --export svg -o art.svg
```

### Show composition statistics

```bash
python3 mondrian.py -s 42 --stats --no-clear
```

### More examples

```bash
# Specific size
python3 mondrian.py -W 100 -H 40

# More subdivisions (higher split probability)
python3 mondrian.py -p 0.95

# Fewer subdivisions (calmer composition)
python3 mondrian.py -p 0.5

# Gallery mode: generate 5 compositions
python3 mondrian.py -n 5

# Fine control over minimum region size and depth
python3 mondrian.py -m 4 -d 8

# No signature watermark
python3 mondrian.py --no-signature
```

### As a Python Library

```python
from mondrian import generate_mondrian

# Generate art as an ANSI string
art, canvas, palette = generate_mondrian(width=80, height=30, seed=42)
print(art)

# Custom parameters
art, canvas, palette = generate_mondrian(
    width=100, height=40,
    seed=1337,
    split_prob=0.9,
    max_depth=7,
    min_size=4,
    palette_name="neon",
    no_signature=True
)
print(art)

# Export to file
from mondrian import export_svg, export_html
export_svg(canvas, palette, "output.svg")
export_html(canvas, palette, "output.html")

# Get composition statistics
from mondrian import count_regions
stats = count_regions(canvas, palette)
print(stats)
# {'total_cells': 523, 'colors': {'red': 102, 'blue': 78, 'yellow': 343}}
```

## All Options

| Flag | Default | Description |
|------|---------|-------------|
| `-W` / `--width` | auto-detect | Canvas width in characters |
| `-H` / `--height` | auto-detect | Canvas height in rows |
| `-s` / `--seed` | random | Random seed for reproducible art |
| `-p` / `--palette` | classic | Color palette (classic, neon, pastel, seventies, dark) |
| `--split-prob` | 0.85 | Probability of splitting a region (0.0–1.0) |
| `-d` / `--max-depth` | 6 | Maximum subdivision depth |
| `-m` / `--min-size` | 6 | Minimum region size before splitting stops |
| `-n` / `--count` | 1 | Number of compositions to generate |
| `--no-clear` | off | Don't clear the screen before drawing |
| `--no-signature` | off | Omit the MONDRIAN signature watermark |
| `--animate` | off | Animate the composition being drawn row by row |
| `--delay` | 0.03 | Delay in seconds between animation frames |
| `--export` | — | Export format: `svg` or `html` |
| `-o` / `--output` | mondrian.svg/html | Output file path for exports |
| `--stats` | off | Print composition statistics after rendering |
| `--version` | — | Show version number |

## Palettes

| Palette | Description |
|---------|-------------|
| `classic` | Authentic Mondrian colors — bold red, deep blue, bright yellow, off-white |
| `neon` | Vibrant neon colors — hot pink, cyan, electric yellow |
| `pastel` | Soft pastel tones — rose, sky blue, pale yellow |
| `seventies` | Warm retro palette — earthy red, navy, mustard |
| `dark` | Dark background with bright accents — Dracula-inspired |

## How It Works

1. **Canvas initialization** — Creates a 2D grid of cells, each with a character, foreground color, and background color. The entire canvas starts as off-white (or the palette's white).

2. **Recursive subdivision** — Starting from the full canvas (minus outer border), the algorithm decides whether to split (based on `split_prob`, size constraints, and depth), chooses horizontal or vertical direction (preferring the longer axis), picks a random split position, draws thick black borders at the split, and recursively processes each sub-region.

3. **Color filling** — Leaf regions (ones that aren't split further) are filled with a random color from the Mondrian palette. White is weighted more heavily, as in real Mondrian paintings.

4. **Border intersection fixing** — A second pass identifies where horizontal and vertical borders cross and replaces the characters with the correct intersection symbols (┼, ┬, ┴, ├, ┤).

5. **Rendering** — Each cell is rendered as an ANSI-escaped string with both foreground and background 24-bit color codes, producing a seamless grid of colored rectangles separated by black lines.

## Testing

```bash
python3 -m pytest test_mondrian.py -v
```

## License

MIT