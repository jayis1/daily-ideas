# ❄ Procedural Snowflake Generator

**Version 2.1.0** — Generate unique, mathematically-derived snowflake crystal patterns using fractal branching algorithms. No two are alike — just like real snowflakes!

Each snowflake is deterministic from its seed string, so the same seed always produces the same crystal. The generator simulates dendritic arm growth with randomized branching, producing 5 crystal types: Dendrite, Plate, Stellar, Fernlike, and Columnar.

## Features

- **5 crystal types**: Dendrite, Plate, Stellar, Fernlike, Columnar — selected by seed
- **Configurable symmetry**: 4-fold, 6-fold (default), 8-fold, or 12-fold rotational symmetry
- **6-fold mirror symmetry**: All snowflakes also have mirror symmetry, as in nature
- **Koch-curve edges**: Plate and Stellar crystals get small faceted edge decorations
- **Deterministic seeds**: Same seed = same snowflake, every time
- **6 color palettes**: frost, aurora, ice, ember, violet, mono
- **Animation mode**: Watch your snowflake fall through a starry sky with gentle sway
- **Gallery mode**: View multiple snowflakes side-by-side
- **Compare mode**: Compare two seeds side by side (`--compare`)
- **SVG export**: Generate vector art snowflakes for print or web, with palette-aware colors
- **JSON export**: Export structured snowflake data for programmatic use (`--json`)
- **Crystal report**: Show detailed growth parameters derived from the seed (`--info`)
- **Configurable depth**: Control complexity from simple plates to intricate dendrites (1–5)
- **Version flag**: `--version` for version checking
- **Input validation**: Depth and size are automatically clamped to valid ranges
- **`--no-color` support**: All rendering modes (render, gallery, compare, info, animate) respect the `--no-color` flag
- **SVG XSS prevention**: Seed names and crystal types are HTML-escaped in SVG output
- **No external dependencies**: Uses only the Python standard library

## How to Install

No external dependencies — uses only the Python standard library:

```bash
# No install needed, just run it!
python3 snowflake.py
```

## How to Run

```bash
# Generate a random snowflake
python3 snowflake.py

# Generate with a specific seed
python3 snowflake.py -s "winter-storm"

# Choose a color palette (frost, aurora, ice, ember, violet, mono)
python3 snowflake.py -s "aurora" -p aurora

# Choose symmetry (4, 6, 8, or 12)
python3 snowflake.py -s "crystal" --symmetry 8

# Disable colors (for pipes, files, or non-TTY output)
python3 snowflake.py -s "plain" --no-color

# Animate the snowflake falling through the sky
python3 snowflake.py -s "gentle-snow" --animate

# Generate a gallery of 4 snowflakes
python3 snowflake.py -s "gallery" --gallery 4

# Gallery without colors
python3 snowflake.py -s "gallery" --gallery 4 --no-color

# Compare two seeds side by side
python3 snowflake.py --compare "fire" "ice"

# Compare without colors
python3 snowflake.py --compare "fire" "ice" --no-color

# Export as SVG (with palette colors)
python3 snowflake.py -s "crystal" --svg snowflake.svg

# Export as SVG with aurora palette
python3 snowflake.py -s "aurora" -p aurora --svg aurora.svg

# Export as JSON (to file)
python3 snowflake.py -s "data" --json snowflake.json

# Export as JSON (to stdout — pure JSON, no rendering)
python3 snowflake.py -s "data" --json -

# Show crystal growth parameters
python3 snowflake.py -s "frost" --info

# Show crystal report without colors
python3 snowflake.py -s "frost" --info --no-color

# Control complexity with depth (1-5, default 4)
python3 snowflake.py -s "simple" -d 2

# Larger canvas (11-199, automatically made odd)
python3 snowflake.py -s "detailed" --size 71

# Show version
python3 snowflake.py --version
```

## Usage Examples

### Deterministic Seeds

Every seed produces a unique, reproducible snowflake:

```
$ python3 snowflake.py -s "hello" --no-color --size 21
```

The seed `"hello"` will always produce the exact same crystal. This makes it perfect for:
- Generating avatar-like identifiers
- Creating deterministic art from names or IDs
- Reproducible demonstrations

### Crystal Types

The seed determines the crystal type:

| Type       | Description                                        |
|------------|----------------------------------------------------|
| Dendrite   | Classic branching arms with side branches          |
| Plate       | Simple hexagonal plates with Koch-curve faceted edges |
| Stellar     | Star-like arms with moderate side growth            |
| Fernlike   | Dense, recursive branching resembling fern fronds  |
| Columnar    | Elongated arms with sparse side growth             |

### Symmetry Modes

Control the rotational symmetry of your snowflake:

| Symmetry | Description |
|----------|-------------|
| 4-fold   | Cross-shaped crystals |
| 6-fold   | Classic hexagonal snowflakes (default) |
| 8-fold   | Octagonal star patterns |
| 12-fold  | Dense radial patterns |

### Color Control

The `--no-color` flag suppresses all ANSI escape codes across every output mode:

- **Render**: No ANSI codes in the snowflake display or header
- **Gallery**: Plain-text gallery with no color codes
- **Compare**: Side-by-side comparison without ANSI codes
- **Info**: Crystal report without bold/formatting codes
- **Animate**: Animation without ANSI color codes
- Color is also automatically disabled when stdout is not a TTY (piped output)

### JSON Export

Use `--json -` for machine-readable output (pure JSON on stdout, no rendering):

```bash
python3 snowflake.py -s "data" --json - | python3 -m json.tool
```

The JSON output includes: seed, crystal type, symmetry, max depth, version, and all polar-coordinate segments with depth and branch type.

### Animation

The `--animate` flag renders an animated snowflake falling through a starry night sky with gentle horizontal sway. Color can be disabled with `--no-color`.

### Gallery Mode

Use `--gallery N` to display N snowflakes side-by-side for comparison.

### Compare Mode

Use `--compare SEED_A SEED_B` to render two specific seeds side by side with a dividing line.

## How It Works

The generator uses a seeded pseudo-random number generator (based on SHA-256 hashing with an LCG) to control:

1. **Crystal type selection** from the 5 real-world categories
2. **Arm length and growth factors** for recursive branching
3. **Branch count per depth level** (varying by crystal type)
4. **Branch angles and positions** along each arm
5. **Koch-curve edge decoration** for Plate and Stellar types

Growth starts from the center and recursively branches outward. Each arm is grown with `_grow_arm()`, which adds center-line segments and side branches. For Plate and Stellar crystal types, `_add_koch_edge()` adds small triangular faceted bumps along main arms, mimicking real hexagonal ice crystal facets.

After generation, the segments are reflected with configurable rotational symmetry (4/6/8/12-fold) plus mirror symmetry, producing the characteristic symmetric pattern.

The ASCII renderer maps depth levels to different box-drawing characters (◆ → ┃ → ╎ → ┊ → ·), creating a visual sense of structural hierarchy.

## Running Tests

```bash
python3 -m pytest test_snowflake.py -v
```

The test suite covers:
- SeededRNG: determinism, range validation, shuffle, empty-sequence errors
- Segment creation and serialization (`.to_dict()`)
- Snowflake generation: all crystal types, custom symmetry, depth clamping
- Rendering: with/without color, with/without info, custom symmetry
- **No-color mode**: ANSI suppression verified for render, gallery, compare, info, and CLI
- **SVG XSS prevention**: HTML escaping of `<`, `>`, `&`, `"` characters in seed/crystal type
- Export: SVG (with palette, with escaping), JSON (structure and keys)
- Gallery and compare modes (with and without color)
- `print_seed_info` color parameter
- `animate_snowfall` color parameter existence
- CLI: help, version, seed, gallery, info, symmetry, JSON, SVG, compare flags

## What's New in v2.1.0

### Bug Fixes
- **`--no-color` now works everywhere**: Previously, `--no-color` only suppressed color in the main snowflake render. It now correctly suppresses ANSI codes in:
  - Gallery mode (`--gallery`)
  - Compare mode (`--compare`)
  - Info mode (`--info`)
  - Animation mode (`--animate`)
  - Render mode header text
- **SVG XSS/injection prevention**: Seeds and crystal types containing `<`, `>`, `&`, or `"` characters are now properly HTML-escaped in SVG output, preventing malformed SVG and potential XSS attacks.
- **`generate_gallery()` now accepts `color` parameter**: Gallery rendering can now be colorless, matching the behavior of other rendering functions.
- **`animate_snowfall()` now accepts `color` parameter**: Animation can now be rendered without ANSI color codes.
- **`print_seed_info()` now accepts `color` parameter**: Crystal report header respects the color flag.
- **`main()` now passes `color` to all rendering functions**: Gallery, info, and animate calls now receive the `color` flag derived from `--no-color` and TTY detection.

### Improvements
- **Type hints**: Added `Optional[str]` type hints for color grid arrays in `animate_snowfall()` and `generate_gallery()`.
- **69 tests**: Added 16 new tests covering no-color mode, SVG escaping, seed info color, and animation color parameter.

## What Was New in v2.0.0

- **`--symmetry` flag**: Choose 4, 6, 8, or 12-fold rotational symmetry
- **`--compare` mode**: Side-by-side comparison of two seeds
- **`--json` export**: Machine-readable JSON output (file or stdout with `-`)
- **`--version` flag**: Print version and exit
- **Koch-curve edges**: Plate and Stellar crystals now have faceted edge decorations
- **SVG palette support**: SVG export respects the chosen color palette
- **Input validation**: Depth and size are automatically clamped to valid ranges
- **`Segment.to_dict()`**: Serialize segments for JSON export
- **`SeededRNG.shuffle()`**: Fisher-Yates shuffle for future use
- **Type hints**: Full type annotations throughout the codebase
- **Better docstrings**: Detailed docstrings with argument descriptions

## What It Does

This tool generates procedural snowflake art inspired by the real physics of ice crystal formation. While simplified, it captures the essential idea that temperature and humidity determine crystal morphology — encoded here in the seed string. The result is a unique, shareable piece of generative art for every seed.