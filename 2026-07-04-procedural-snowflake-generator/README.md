# ❄ Procedural Snowflake Generator

Generate unique, mathematically-derived snowflake crystal patterns using fractal branching algorithms. No two are alike — just like real snowflakes!

Each snowflake is deterministic from its seed string, so the same seed always produces the same crystal. The generator simulates dendritic arm growth with randomized branching, producing 5 crystal types: Dendrite, Plate, Stellar, Fernlike, and Columnar.

## Features

- **5 crystal types**: Dendrite, Plate, Stellar, Fernlike, Columnar — selected by seed
- **6-fold symmetry**: All snowflakes have hexagonal crystal symmetry (as in nature)
- **Deterministic seeds**: Same seed = same snowflake, every time
- **6 color palettes**: frost, aurora, ice, ember, violet, mono
- **Animation mode**: Watch your snowflake fall through a starry sky
- **Gallery mode**: View multiple snowflakes side-by-side
- **SVG export**: Generate vector art snowflakes for print or web
- **Crystal report**: Show detailed growth parameters derived from the seed
- **Configurable depth**: Control complexity from simple plates to intricate dendrites

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

# Animate the snowflake falling through the sky
python3 snowflake.py -s "gentle-snow" --animate

# Generate a gallery of 4 snowflakes
python3 snowflake.py -s "gallery" --gallery 4

# Export as SVG
python3 snowflake.py -s "crystal" --svg snowflake.svg

# Show crystal growth parameters
python3 snowflake.py -s "frost" --info

# Control complexity with depth (1-5, default 4)
python3 snowflake.py -s "simple" -d 2

# Larger canvas
python3 snowflake.py -s "detailed" --size 71

# No colors (for pipes/files)
python3 snowflake.py -s "plain" --no-color
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
| Plate       | Simple hexagonal plates, minimal branching         |
| Stellar     | Star-like arms with moderate side growth            |
| Fernlike   | Dense, recursive branching resembling fern fronds  |
| Columnar    | Elongated arms with sparse side growth             |

### Animation

The `--animate` flag renders an animated snowflake falling through a starry night sky with gentle horizontal sway.

### Gallery Mode

Use `--gallery N` to display N snowflakes side-by-side for comparison.

## How It Works

The generator uses a seeded pseudo-random number generator (based on SHA-256 hashing) to control:

1. **Crystal type selection** from the 5 real-world categories
2. **Arm length and growth factors** for recursive branching
3. **Branch count per depth level** (varying by crystal type)
4. **Branch angles and positions** along each arm

Growth starts from the center and recursively branches outward. Each arm is grown with `_grow_arm()`, which adds center-line segments and side branches. After generation, the segments are reflected with 6-fold rotational symmetry plus mirror symmetry, producing the characteristic hexagonal pattern.

The ASCII renderer maps depth levels to different box-drawing characters (◆ → ┃ → ╎ → ┊ → ·), creating a visual sense of structural hierarchy.

## Running Tests

```bash
python3 -m pytest test_snowflake.py -v
```

## What It Does

This tool generates procedural snowflake art inspired by the real physics of ice crystal formation. While simplified, it captures the essential idea that temperature and humidity determine crystal morphology — encoded here in the seed string. The result is a unique, shareable piece of generative art for every seed.