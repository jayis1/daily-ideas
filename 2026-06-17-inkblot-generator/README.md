# 🦋 Procedural Inkblot Generator

Generate Rorschach-style symmetric inkblots in your terminal using procedural noise, rendered as Braille art with whimsical psychological interpretations.

Each run produces a unique inkblot — no two are alike (unless you use the same seed).

![Terminal Output](https://img.shields.io/badge/terminal-braille%20art-blue)

## Features

- **5 inkblot styles** with distinct visual characteristics:
  - `splash` — Classic Rorschach-style symmetric blobs with radial falloff
  - `radial` — Spoke/dendrite patterns radiating from center
  - `cellular` — Voronoi-like cellular structures with organic boundaries
  - `organic` — Tendrils and worm-like forms emanating from center
  - `mirror4` — Four-fold symmetric patterns (mirrored on both axes)
- **Braille art rendering** — Uses Unicode Braille characters (2×4 dot grids) for high-resolution terminal art
- **Psychological interpretations** — Each inkblot comes with a whimsical Rorschach-style reading (objects, emotions, advice)
- **Reproducible output** — Use `--seed` to recreate any inkblot exactly
- **Animation mode** — Watch the inkblot form line by line with `--animate`
- **Configurable size** — Adjust width and height to fit your terminal
- **Zero dependencies** — Pure Python, no external packages needed

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

# Reproduce a specific inkblot
python inkblot.py --seed 42

# Choose a style
python inkblot.py --style splash
python inkblot.py --style radial
python inkblot.py --style cellular
python inkblot.py --style organic
python inkblot.py --style mirror4

# Adjust size (width in Braille characters, height auto-calculated)
python inkblot.py --width 100

# Skip the interpretation
python inkblot.py --no-interpret

# Animate the blot forming
python inkblot.py --animate

# List available styles
python inkblot.py --list-styles

# Combine options
python inkblot.py --seed 42 --style organic --width 60 --no-interpret
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
║                      seed=42  style=splash  size=160×80px                      ║
╚────────────────────────────────────────────────────────────────────────────────╝

┌─ Rorschach Interpretation ──────────────────────────────────────────────────────┐
│       You see two dancers frozen mid-waltz.                                    │
│  This suggests the duality of your creative and analytical selves.             │
│  Symmetry suggests balance. Seek equilibrium in your decisions.                │
└─────────────────────────────────────────────────────────────────────────────────┘

  💡 Rerun with: python inkblot.py --seed 42 --style splash
```

### Four-fold symmetry
```
$ python inkblot.py --seed 777 --style mirror4
```

### Voronoi cellular pattern
```
$ python inkblot.py --seed 555 --style cellular
```

### Narrow terminal-friendly output
```
$ python inkblot.py --width 50 --style radial --no-interpret
```

## How It Works

1. **Procedural noise generation** — Uses value noise with fractal Brownian motion (fBm) to create organic, natural-looking patterns
2. **Symmetry** — Each style applies different mirroring operations to create Rorschach-like bilateral or four-fold symmetry
3. **Braille rendering** — The 2D boolean grid is converted to Unicode Braille characters, where each character encodes a 2×4 pixel grid (8 possible dots per cell)
4. **Interpretation** — A seeded random selection picks from curated lists of objects, emotions, and advice to create whimsical psychological readings

## File Structure

```
inkblot-generator/
├── inkblot.py     # Complete implementation (single file)
└── README.md      # This file
```

## Extending

- Add new styles by defining a function with signature `generate_xxx(height, width, seed, rng)` that returns a 2D boolean grid, then adding it to the `STYLES` dict
- Add new interpretations by extending the `INTERPRETATIONS` dict
- Adjust thresholds in generators for denser or sparser blots