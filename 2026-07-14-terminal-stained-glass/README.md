# 🏛️ Terminal Stained Glass Generator

Procedurally generate beautiful stained glass window patterns directly in your terminal! Each window features colored Unicode characters arranged in authentic architectural styles — from Gothic cathedrals to Art Deco masterpieces.

## Features

- **6 Architectural Styles**: Gothic, Romanesque, Art Nouveau, Art Deco, Byzantine, and Modern Minimalist
- **Deterministic Seeds**: Reproduce any window exactly with the `--seed` flag
- **Authentic Lead Lines**: Each style uses characteristic lead patterns (pointed arches, rounded arches, organic curves, geometric chevrons, mosaic grids, clean bands)
- **Rich Color Palettes**: Each style has a curated color palette using 256-color ANSI terminal colors
- **Varied Glass Textures**: Uses multiple Unicode characters (█, ▓, ◆, ●, ★, ✦, ✿, ◈, etc.) for realistic glass texture
- **Auto-sizing**: Automatically adapts to your terminal dimensions
- **Batch Generation**: Generate multiple windows at once with `--count`

## Installation

No external dependencies needed — just Python 3.6+!

```bash
# Clone or download
git clone <repo-url>
cd terminal-stained-glass

# Make executable (optional)
chmod +x stained_glass.py
```

## Usage

### Basic — pick a style and generate

```bash
python3 stained_glass.py -s gothic
```

### Specify dimensions and seed for reproducibility

```bash
python3 stained_glass.py -s art_deco -w 80 -H 40 --seed 42
```

### List all available styles

```bash
python3 stained_glass.py --list-styles
```

### Generate multiple windows

```bash
python3 stained_glass.py -s byzantine -n 3 --seed 100
```

## Command-Line Options

| Flag | Short | Description |
|------|-------|-------------|
| `--style` | `-s` | Architectural style: `gothic`, `romanesque`, `art_nouveau`, `art_deco`, `byzantine`, `modern` |
| `--width` | `-w` | Window width in characters (default: auto-detect terminal) |
| `--height` | `-H` | Window height in characters (default: auto-detect terminal) |
| `--seed` | | Random seed for reproducible output |
| `--count` | `-n` | Number of windows to generate |
| `--list-styles` | | Show all available styles with descriptions |

## Architectural Styles

| Style | Description |
|-------|-------------|
| **gothic** | Tall pointed arches with deep jewel tones (red, blue, gold, violet) |
| **romanesque** | Rounded arches with warm Mediterranean tones (blue, teal, amber, orange) |
| **art_nouveau** | Flowing organic shapes with pastel accents (lime, teal, violet, pink) |
| **art_deco** | Bold geometric chevron patterns with gold and jewel tones |
| **byzantine** | Rich gold and jewel tones in mosaic grid patterns with a central medallion |
| **modern** | Clean horizontal bands with bright primary colors |

## How It Works

1. **Frame Drawing**: The generator draws an architectural frame based on the chosen style (pointed arch for Gothic, rounded arch for Romanesque, etc.)
2. **Lead Pattern**: Decorative lead lines are drawn inside the frame, creating distinct regions characteristic of each style
3. **Flood Fill**: A flood-fill algorithm identifies each enclosed region of glass
4. **Color Assignment**: Each region receives a color from the style's palette, with spatial coherence so adjacent regions tend to have different colors. Small regions may receive accent colors.
5. **Texture**: Each region is filled with a mix of Unicode glass characters for visual texture and realism

## Examples

```
$ python3 stained_glass.py -s gothic --seed 42

╔│══════════════════════════════════════════════════════════════════│╗
║│──────────────────────────────────────────────────────────────────│║
║│♥♥♥♥♥♥✺♥♥♥♥♥♥♥♥♥♥♥/♥♥♥♥♥♥♥♥♥\♥♥♥∿♥♥█♥♥/♥♥♥♥♥♥♥♥•\█♥♥♥♥♥♥♥♥♥█♥♥♥♥♥♥│║
║││♥♥♥◈♥♥♥♥♥♥♥♥♥♥♥♥/♥♥♥♥♥♥♥♥♥♥♥\♥★♥♥♥♥▓/♥♥✺♥♥●█♥♥♥♥▓\♥★♥♥♥▒♥♥◆♥♥♥░♥✦♥│║
...
```

## Requirements

- Python 3.6+
- A terminal that supports 256-color ANSI escape codes (most modern terminals do)

## License

MIT