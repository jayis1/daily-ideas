# 🦋 Procedural Inkblot Generator

**Version 2.0.0**

Generate Rorschach-style symmetric inkblots in your terminal using procedural noise, rendered as Braille art with whimsical psychological interpretations.

Each run produces a unique inkblot — no two are alike (unless you use the same seed).

![Terminal Output](https://img.shields.io/badge/terminal-braille%20art-blue) ![Python 3.6+](https://img.shields.io/badge/python-3.6%2B-green) ![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)

## Features

### Inkblot Styles (6 total)
- **`splash`** — Classic Rorschach-style symmetric blobs with radial falloff
- **`radial`** — Spoke/dendrite patterns radiating from center
- **`cellular`** — Voronoi-like cellular structures with organic boundaries
- **``organic`** — Tendrils and worm-like forms emanating from center
- **`mirror4`** — Four-fold symmetric patterns (mirrored on both axes)
- **`fractal`** *(new!)* — Branching dendrite patterns like neurons or rivers

### Rendering & Display
- **Braille art rendering** — Uses Unicode Braille characters (2×4 dot grids) for high-resolution terminal art
- **ANSI color support** — Color the inkblot with `--color` (magenta, cyan, blue, red, green, yellow, white, and bright variants)
- **Gallery mode** — Show a 2×2 grid of 4 different styles side-by-side with `--gallery`
- **Animation mode** — Watch the inkblot form line by line with `--animate`
- **Invert mode** — Swap ink and paper with `--invert`

### Configuration
- **Reproducible output** — Use `--seed` to recreate any inkblot exactly
- **Density control** — Adjust how dense/sparse the blot is with `--density` (0.1–0.9)
- **Configurable size** — Set `--width` and `--height` to fit your terminal
- **Statistics** — Show fill ratio, pixel count, and symmetry score with `--stats`
- **Save to file** — Write output to a text file with `--save` (strips ANSI codes automatically)

### Interpretations
- **Psychological interpretations** — Each inkblot comes with a whimsical Rorschach-style reading (objects, emotions, advice)
- **Expanded interpretation pool** — 12 entries per category (up from 10) for more variety

### Quality of Life
- **`--version` flag** — Print the version number
- **`--help` flag** — Full usage instructions with examples
- **`--list-styles`** — List all available styles with descriptions
- **Input validation** — Rejects invalid width/density values with helpful error messages
- **Zero dependencies** — Pure Python standard library, no pip install needed

## How to Install

```bash
# No installation needed! Just clone and run.
git clone <repo-url>
cd inkblot-generator

# Or just download the single file
curl -O <raw-url>/inkblot.py
```

Requires Python 3.6+ (uses only standard library). No pip install needed.

## How to Run

```bash
# Generate a random inkblot
python inkblot.py

# Show version
python inkblot.py --version

# Reproduce a specific inkblot
python inkblot.py --seed 42

# Choose a style
python inkblot.py --style splash
python inkblot.py --style radial
python inkblot.py --style cellular
python inkblot.py --style organic
python inkblot.py --style mirror4
python inkblot.py --style fractal

# Adjust size (width in Braille characters, height auto-calculated)
python inkblot.py --width 100
python inkblot.py --width 60 --height 40

# Skip the interpretation
python inkblot.py --no-interpret

# Animate the blot forming
python inkblot.py --animate

# Invert the inkblot (swap ink/paper)
python inkblot.py --invert

# Add color
python inkblot.py --color magenta
python inkblot.py --color cyan
python inkblot.py --color bright_blue

# Control density (0.1 = sparse, 0.9 = dense)
python inkblot.py --density 0.7

# Show blot statistics
python inkblot.py --stats

# Save output to a file (ANSI codes stripped automatically)
python inkblot.py --seed 42 --save my_blot.txt

# Gallery mode — show 4 styles side by side
python inkblot.py --gallery

# List available styles
python inkblot.py --list-styles

# Combine options
python inkblot.py --seed 42 --style organic --color magenta --density 0.5 --stats
```

## Usage Examples

### Classic Rorschach blot
```
$ python inkblot.py --seed 42 --style splash

╔────────────────────────────────────────────────────────────────────────────────╗
║                               RORSCHACH INKBLOT                                ║
╠────────────────────────────────────────────────────────────────────────────────╣
║         ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠠⠂⠀⠀⠀         ║
║         ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⢌⢈⠈⠀⡀⡾⠉⢐⣧⠄⠀⢀⢈⣈⠈         ║
║         ... (symmetric Braille art inkblot) ...                                ║
╠────────────────────────────────────────────────────────────────────────────────╣
║                seed=42  style=splash  size=160×80px                           ║
╚────────────────────────────────────────────────────────────────────────────────╝

┌─ Rorschach Interpretation ──────────────────────────────────────────────────────┐
│       You see two dancers frozen mid-waltz.                                    │
│  This suggests the duality of your creative and analytical selves.             │
│  Symmetry suggests balance. Seek equilibrium in your decisions.                │
└─────────────────────────────────────────────────────────────────────────────────┘

  💡 Rerun with: python inkblot.py --seed 42 --style splash
```

### Fractal dendrite pattern with color and stats
```
$ python inkblot.py --seed 777 --style fractal --color cyan --stats
```

### Gallery of 4 styles
```
$ python inkblot.py --seed 100 --gallery
```

### Inverted blot saved to file
```
$ python inkblot.py --seed 42 --invert --save inverted_blot.txt
```

## What's New in v2.0

- **`fractal` style** — New dendrite pattern with branching structures like neurons or river deltas
- **`--color` flag** — ANSI color support (9 colors + bright variants)
- **`--invert` flag** — Swap ink and paper for a different look
- **`--gallery` mode** — 2×2 grid showing 4 styles at once
- **`--density` control** — Fine-tune how dense or sparse the blot appears (0.1–0.9)
- **`--stats` flag** — Show fill ratio, pixel count, and symmetry score
- **`--save` flag** — Write output to a text file (ANSI codes auto-stripped)
- **`--version` flag** — Print the version number
- **Input validation** — Helpful errors for invalid width/density values
- **Expanded interpretations** — 12 entries per category (was 10)
- **Improved documentation** — Comprehensive docstrings on all public functions
- **46 unit tests** — Full test suite covering Braille encoding, noise, generators, interpretations, stats, inversion, and CLI

## How It Works

1. **Procedural noise generation** — Uses value noise with fractal Brownian motion (fBm) to create organic, natural-looking patterns
2. **Symmetry** — Each style applies different mirroring operations to create Rorschach-like bilateral or four-fold symmetry
3. **Density control** — The `--density` parameter shifts the noise threshold, making blots sparser (low values) or denser (high values)
4. **Braille rendering** — The 2D boolean grid is converted to Unicode Braille characters, where each character encodes a 2×4 pixel grid (8 possible dots per cell)
5. **Interpretation** — A seeded random selection picks from curated lists of objects, emotions, and advice to create whimsical psychological readings

## File Structure

```
inkblot-generator/
├── inkblot.py         # Complete implementation (single file, zero dependencies)
├── test_inkblot.py    # Test suite (46 tests, run with pytest)
└── README.md          # This file
```

## Running Tests

```bash
python3 -m pytest test_inkblot.py -v
```

All 46 tests cover: Braille encoding, colored output, noise functions, all 6 generators, symmetry verification, density control, interpretation generation, statistics, grid inversion, and CLI flags.

## Extending

- **Add new styles** by defining a function with signature `generate_xxx(height, width, seed, rng, density=0.35)` that returns a 2D boolean grid, then adding it to the `STYLES` dict
- **Add new interpretations** by extending the `INTERPRETATIONS` dict
- **Add new colors** by adding entries to `ANSI_COLORS`
- Adjust thresholds in generators for denser or sparser blots, or use `--density` for runtime control