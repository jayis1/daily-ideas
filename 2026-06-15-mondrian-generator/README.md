# 🎨 Terminal Mondrian Art Generator v3.0.1

Generate Piet Mondrian-style **De Stijl** compositions directly in your terminal using Unicode box-drawing characters and ANSI 24-bit true colors.

Every run produces a unique composition. Use a seed for reproducible results.

## What's New in v3.0.1 (Bug Fix Release)

- **Fixed: `draw_outer_border` crash on tiny canvases** — canvases smaller than `BORDER_W` (2) cells in either dimension caused an `IndexError`. The function now safely skips out-of-bounds cells.
- **Fixed: `generate_mondrian` API accepts invalid dimensions** — calling `generate_mondrian(width=1, height=1)` or any canvas smaller than `2×BORDER_W + 1` (5×5) now raises a clear `ValueError` instead of crashing with an `IndexError`.
- **Fixed: `--min-size 1` rejected by CLI** — the `--min-size` validator required `≥ 2` but `1` is a valid value. Now accepts `≥ 1`.
- **Fixed: `--count 0` and `--count -1` accepted** — the CLI now validates that `--count` must be `≥ 1`.
- **Fixed: Negative `--max-depth` accepted** — the CLI now validates that `--max-depth` must be `≥ 0`.
- **Fixed: `--width 0` accepted without error** — the CLI now validates that `--width` and `--height` must be `≥ 1` when explicitly provided.
- **Fixed: `Cell` default bg color bias** — the `Cell` dataclass defaulted to `(242, 242, 242)` (the classic palette's white), causing `count_regions()` and `compute_coverage()` to misidentify cells on canvases using non-classic palettes. Default is now `(0, 0, 0)` (neutral), since `generate_mondrian` always fills the canvas with the palette's white before subdivision.
- **Added: 9 regression tests** for all the above fixes.

## Features

- **Recursive subdivision algorithm** — randomly splits regions horizontally or vertically, preferring the longer axis, creating authentic Mondrian-like compositions
- **7 color palettes** — classic, neon, pastel, 70s retro, dark, ocean, and autumn
- **Custom palettes** — define any 5-color palette via JSON on the command line
- **24-bit ANSI true color** — vivid, accurate color rendering
- **Thick black borders** — 2-character-wide borders rendered with Unicode box-drawing characters (┼, │, ─, ┬, ┴, ├, ┤)
- **Animation mode** — watch the composition being drawn row by row
- **SVG export** — save compositions as scalable vector graphics
- **HTML export** — save compositions as standalone web pages with CSS grid
- **PNG export** — save compositions as PNG images (pure Python, no dependencies)
- **Composition statistics** — see color distribution, cell counts, and percentage coverage
- **Plain text mode** — pipe-friendly output without ANSI escapes
- **Configurable** — control canvas size, split probability, recursion depth, minimum region size, and random seed
- **Gallery mode** — generate multiple compositions sequentially with `-n`
- **Signature watermark** — each composition is signed "MONDRIAN" (opt-out with `--no-signature`)
- **`--version` and `--help`** — standard CLI flags
- **Input validation** — rejects invalid dimensions, negative delays, out-of-range parameters, and zero/negative counts

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
# Classic Mondrian (default)
python3 mondrian.py -p classic

# Neon colors
python3 mondrian.py -p neon

# Pastel colors
python3 mondrian.py -p pastel

# 70s retro
python3 mondrian.py -p seventies

# Dark mode
python3 mondrian.py -p dark

# Ocean blues
python3 mondrian.py -p ocean

# Autumn warmth
python3 mondrian.py -p autumn
```

### List all palettes with swatches

```bash
python3 mondrian.py --list-palettes
```

### Custom palette via JSON

```bash
python3 mondrian.py --custom-palette '{"red":[255,0,0],"blue":[0,0,255],"yellow":[255,255,0],"white":[255,255,255],"black":[0,0,0]}' -W 60 -H 30
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

### Export to SVG, HTML, or PNG

```bash
# Export as SVG
python3 mondrian.py --export svg -o composition.svg

# Export as HTML
python3 mondrian.py --export html -o composition.html

# Export as PNG (default cell size: 10px per character)
python3 mondrian.py --export png -o composition.png

# High-resolution PNG (20px per character cell)
python3 mondrian.py --export png --cell-size 20 -o composition_hd.png

# Specify size and seed for reproducible exports
python3 mondrian.py -W 100 -H 50 -s 42 --export svg -o art.svg
```

### Show composition statistics

```bash
python3 mondrian.py -s 42 --stats --no-clear
```

Output includes color cell counts and percentage coverage:

```
Composition statistics:
  Seed: 42
  Canvas: 80×34
  Palette: classic
  red: 120 cells (4.4%)
  blue: 85 cells (3.1%)
  yellow: 210 cells (7.7%)
  white: 1420 cells (52.2%)
  Border cells: 920 (33.8%)
```

### Plain text mode (for piping)

```bash
python3 mondrian.py -W 40 -H 15 --plain --no-clear
```

Outputs just the box-drawing characters without ANSI color codes — useful for logging or piping to other tools.

### More examples

```bash
# Specific size
python3 mondrian.py -W 100 -H 40

# More subdivisions (higher split probability)
python3 mondrian.py --split-prob 0.95

# Fewer subdivisions (calmer composition)
python3 mondrian.py --split-prob 0.5

# Gallery mode: generate 5 compositions
python3 mondrian.py -n 5

# Fine control over minimum region size and depth
python3 mondrian.py -m 1 -d 8

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
    min_size=1,
    palette_name="neon",
    no_signature=True
)
print(art)

# Custom palette
custom = {
    "red": (255, 0, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "white": (255, 255, 255),
    "black": (0, 0, 0),
}
art, canvas, palette = generate_mondrian(width=60, height=30, custom_palette=custom)

# Export to file
from mondrian import export_svg, export_html, export_png
export_svg(canvas, palette, "output.svg")
export_html(canvas, palette, "output.html")
export_png(canvas, palette, "output.png", cell_size=10)

# Get composition statistics
from mondrian import count_regions, compute_coverage
stats = count_regions(canvas, palette)
coverage = compute_coverage(canvas, palette)
print(stats)     # {'total_cells': 523, 'colors': {'red': 102, 'blue': 78, 'yellow': 343}}
print(coverage)  # {'white': 52.2, 'red': 4.4, 'blue': 3.1, 'yellow': 7.7}

# Plain text rendering (no ANSI escapes)
from mondrian import render_plain
print(render_plain(canvas))
```

**Note:** `generate_mondrian()` raises `ValueError` if the canvas dimensions are too small (minimum 5×5, since the 2-cell border requires 4 cells plus at least 1 cell for content).

## All Options

| Flag | Default | Description |
|------|---------|-------------|
| `-W` / `--width` | auto-detect | Canvas width in characters (must be ≥ 1) |
| `-H` / `--height` | auto-detect | Canvas height in rows (must be ≥ 1) |
| `-s` / `--seed` | random | Random seed for reproducible art |
| `-p` / `--palette` | classic | Color palette (classic, neon, pastel, seventies, dark, ocean, autumn) |
| `--custom-palette` | — | Custom palette as JSON (overrides `--palette`) |
| `--split-prob` | 0.85 | Probability of splitting a region (0.0–1.0) |
| `-d` / `--max-depth` | 6 | Maximum subdivision depth (must be ≥ 0) |
| `-m` / `--min-size` | 6 | Minimum region size before splitting stops (must be ≥ 1) |
| `-n` / `--count` | 1 | Number of compositions to generate (must be ≥ 1) |
| `--no-clear` | off | Don't clear the screen before drawing |
| `--no-signature` | off | Omit the MONDRIAN signature watermark |
| `--animate` | off | Animate the composition being drawn row by row |
| `--delay` | 0.03 | Delay in seconds between animation frames (must be ≥ 0) |
| `--export` | — | Export format: `svg`, `html`, or `png` |
| `-o` / `--output` | mondrian.* | Output file path for exports |
| `--stats` | off | Print composition statistics after rendering |
| `--list-palettes` | off | List available palettes with color swatches and exit |
| `--plain` | off | Output plain text without ANSI escapes |
| `--cell-size` | 10 | Cell size in pixels for PNG export (must be ≥ 1) |
| `--version` | — | Show version number |

## Palettes

| Palette | Description |
|---------|-------------|
| `classic` | Authentic Mondrian colors — bold red, deep blue, bright yellow, off-white |
| `neon` | Vibrant neon colors — hot pink, cyan, electric yellow |
| `pastel` | Soft pastel tones — rose, sky blue, pale yellow |
| `seventies` | Warm retro palette — earthy red, navy, mustard |
| `dark` | Dark background with bright accents — Dracula-inspired |
| `ocean` | Cool ocean blues — coral red, deep blue, sandy yellow, seafoam white |
| `autumn` | Warm autumn tones — brick red, slate blue, goldenrod, cream |

## How It Works

1. **Canvas initialization** — Creates a 2D grid of cells, each with a character, foreground color, and background color. The entire canvas is filled with the palette's white color.

2. **Recursive subdivision** — Starting from the full canvas (minus outer border), the algorithm decides whether to split (based on `split_prob`, size constraints, and depth), chooses horizontal or vertical direction (preferring the longer axis), picks a random split position, draws thick black borders at the split, and recursively processes each sub-region.

3. **Color filling** — Leaf regions (ones that aren't split further) are filled with a random color from the Mondrian palette. White is weighted more heavily (4:1 ratio), as in real Mondrian paintings.

4. **Border intersection fixing** — A second pass identifies where horizontal and vertical borders cross and replaces the characters with the correct intersection symbols (┼, ┬, ┴, ├, ┤).

5. **Rendering** — Each cell is rendered as an ANSI-escaped string with 24-bit foreground and background color codes, producing a seamless grid of colored rectangles separated by black lines. The optimized renderer batches consecutive cells with the same color to reduce escape sequence overhead.

## PNG Export

The PNG exporter is implemented in pure Python using `struct` and `zlib` — no external dependencies like Pillow are required. Each character cell is rendered as a square block of `cell_size × cell_size` pixels, producing clean, pixel-perfect Mondrian compositions that can be shared as images.

## Testing

```bash
python3 -m pytest test_mondrian.py -v
```

The test suite includes 68 tests covering:
- Version format validation
- Canvas creation, fill, and boundary checks
- Rect.area() utility
- Dimension validation (too-small canvases raise ValueError)
- Deterministic and varied generation
- All 7 palettes and custom palettes
- Small canvas edge cases
- ANSI output and box-drawing characters
- Plain text rendering (no ANSI escapes)
- Coverage percentage computation
- SVG, HTML, and PNG export validity
- PNG export with custom cell sizes
- Composition statistics with percentage coverage
- Custom palette JSON parsing (valid, missing, extra, invalid)
- CLI flags: `--version`, `--help`, `--list-palettes`, `--plain`, `--custom-palette`
- Regression tests for input validation (zero/negative dimensions, negative delay, count ≥ 1, max-depth ≥ 0, min-size ≥ 1, width/height ≥ 1)
- draw_outer_border safety on tiny canvases
- count_regions correctness with non-classic palettes
- SVG explicit coordinate attributes
- HTML border-cell class distinction
- Stats formatting in export mode

## Changelog

### v3.0.1 (Bug Fix Release)

- **Fixed: `draw_outer_border` crash on tiny canvases** — canvases smaller than 5×5 caused an `IndexError` when drawing the outer border. Now safely handles any canvas size.
- **Fixed: `generate_mondrian` API crash on small dimensions** — calling with `width < 5` or `height < 5` now raises a clear `ValueError` instead of an opaque `IndexError`.
- **Fixed: `--min-size 1` rejected by CLI** — the minimum was incorrectly set to 2; now correctly accepts values ≥ 1.
- **Fixed: `--count 0` and `--count -1` accepted** — the CLI now validates that count must be ≥ 1.
- **Fixed: Negative `--max-depth` accepted** — the CLI now validates that max-depth must be ≥ 0.
- **Fixed: `--width 0` and `--height 0` accepted** — the CLI now validates that explicitly provided dimensions must be ≥ 1.
- **Fixed: `Cell` default bg color biased toward classic palette** — changed from `(242, 242, 242)` to `(0, 0, 0)`. The `generate_mondrian` function already fills the entire canvas with the palette's white before subdivision, so this change only affects manually created canvases and ensures `count_regions`/`compute_coverage` work correctly with all palettes.
- **Added: 9 regression tests** for all the above fixes.

### v3.0 (Feature Release)

- **Added: PNG export** — `--export png` saves compositions as PNG images using pure Python (no Pillow needed)
- **Added: `--cell-size` flag** — control pixel resolution for PNG export (default: 10)
- **Added: 2 new palettes** — `ocean` (cool blues) and `autumn` (warm earth tones)
- **Added: `--custom-palette` flag** — define any 5-color palette from the command line via JSON
- **Added: `--list-palettes` flag** — display all palettes with ANSI color swatches
- **Added: `--plain` mode** — output box-drawing characters without ANSI escape codes, for piping
- **Added: `compute_coverage()` function** — calculate percentage coverage per color
- **Added: Stats now show percentage coverage** — `--stats` displays `red: 120 cells (4.4%)` format
- **Added: Stats now show border cell count and percentage**
- **Added: Custom signature text** — `add_signature()` accepts custom text parameter
- **Added: `Rect.area()` method** — convenience method on Rect dataclass
- **Improved: Rendering optimization** — batch consecutive same-color cells to reduce ANSI escape sequences
- **Improved: Intersection detection** — better handling of border junction characters and edge cases
- **Updated: CLI help examples** — now includes PNG export and `--list-palettes` examples

### v2.1 (Bug Fix Release)

- **Fixed: Negative delay accepted without error**
- **Fixed: Export mode stats used raw dict repr**
- **Fixed: SVG background rect missing explicit x/y**
- **Fixed: HTML export dead code**
- **Fixed: Zero-size canvas accepted without error**

## License

MIT