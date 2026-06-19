# 🏴 Procedural Flag Generator

A creative CLI tool that generates random fictional country flags with various geometric patterns and renders them as colorful Unicode block art directly in your terminal. Every flag comes with a procedurally generated country name, a unique pattern combination, and a color palette drawn from real-world vexillological traditions.

## Features

- **12 pattern types**: horizontal stripes, vertical stripes, diagonal, Nordic cross, saltire (X-cross), chevron, quarters, central circle, crescent, star, canton, and diamond
- **4 emblem overlays**: star, circle, crescent, and scattered star fields — randomly applied on ~50% of flags
- **27 named colors** from real flag traditions (crimson, navy, gold, etc.)
- **Procedural country name generator** combining prefixes, roots, and suffixes for names like "Northern Valastan" or "Golden Miraniamer"
- **Half-block rendering** using Unicode `▀` for 2× vertical resolution — flags look crisp and proportional
- **ASCII mode** for non-terminal contexts with bordered character-art output
- **Deterministic seeding** — generate the same flag every time with `--seed`
- **Flag of the Day** — a unique daily flag based on the current date
- **Gallery mode** — show 4 flags side-by-side
- **Customizable dimensions** — adjust width and height to fit your terminal

## Installation

No external dependencies required — uses only Python 3 standard library.

```bash
# Clone and run
git clone <repo-url>
cd procedural-flag-generator
python3 flag_generator.py
```

## Usage

```bash
# Generate a single random flag
python3 flag_generator.py

# Generate the flag of the day (same flag for everyone on the same date)
python3 flag_generator.py --daily

# Generate 5 random flags
python3 flag_generator.py -n 5

# Generate a gallery of 4 flags
python3 flag_generator.py --gallery

# Use a specific seed for reproducibility
python3 flag_generator.py --seed 42

# Output as ASCII art (for pipes, logs, non-terminal contexts)
python3 flag_generator.py --ascii

# Custom country name
python3 flag_generator.py --name "United Republic of Dave"

# Custom dimensions
python3 flag_generator.py -W 80 -H 50

# Combine options
python3 flag_generator.py --gallery --seed 7 --name "Kingdom of Zela"
```

## Examples

### Random Flag
```
python3 flag_generator.py --seed 7
```
Outputs a colorful diagonal flag for "Ancient Zelaashagard" with a chevron pattern in multiple colors.

### Flag of the Day
```
python3 flag_generator.py --daily
```
Generates "Golden Juramiraia" — a navy flag with a coral crescent, consistent for everyone on June 19, 2026.

### ASCII Mode
```
python3 flag_generator.py --ascii
```
Renders flags using characters like `#`, `@`, `%`, `&` inside bordered boxes — great for saving to files.

### Gallery
```
python3 flag_generator.py --gallery
```
Displays 4 random flags with pattern descriptions and color legends.

## Pattern Types

| Pattern     | Description                                      | Real-World Analog      |
|-------------|--------------------------------------------------|------------------------|
| horizontal  | Horizontal color bands                           | Germany, Netherlands   |
| vertical    | Vertical color bands                             | France, Italy          |
| diagonal    | Diagonal split from corner to corner             | Republic of the Congo  |
| cross       | Nordic off-center cross                          | Sweden, Finland         |
| saltire     | X-shaped cross                                   | Scotland, Jamaica      |
| chevron     | V-shape on the hoist side                       | Czech Republic         |
| quarters    | Four colored quadrants                           | Panama, Dominican Rep. |
| circle      | Central circular emblem                         | Japan, Bangladesh      |
| crescent    | Crescent moon shape                             | Turkey, Pakistan       |
| star        | Five-pointed star on a field                     | Many national flags    |
| canton      | Colored rectangle in upper-hoist over stripes    | USA, Liberia            |
| diamond     | Central diamond shape                            | Rhodesia               |

## How It Works

1. **Pattern Selection**: A base pattern is randomly chosen from the 12 available types
2. **Color Assignment**: 2–4 colors are sampled from the 27-color palette based on pattern needs
3. **Grid Rendering**: The pattern is painted onto a 60×40 character grid
4. **Emblem Overlay**: With 50% probability, an emblem (star, circle, crescent, or star cluster) is overlaid on the grid
5. **Name Generation**: A fictional country name is assembled from prefix + root + suffix components
6. **Terminal Output**: The grid is rendered using ANSI 256-color codes and Unicode half-block characters for high-resolution display

## File Structure

```
├── flag_generator.py      # Main program with all pattern generators and renderer
├── test_flag_generator.py # Comprehensive test suite (22 tests)
└── README.md              # This file
```

## Testing

```bash
python3 test_flag_generator.py
```

Runs 22 tests covering grid dimensions, color validity, pattern correctness, name generation, rendering output, determinism, and more.

## License

MIT