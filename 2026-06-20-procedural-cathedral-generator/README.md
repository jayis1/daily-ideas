# 🏛️ Procedural Cathedral Generator

Generate unique ASCII art gothic cathedrals every time! Each run produces a different cathedral with randomized spires, rose windows, stained glass, flying buttresses, arched doors, gargoyles, clock faces, and atmospheric details — now with optional ANSI color, weather effects, and JSON metadata output.

## Features

- **Procedural generation** — every cathedral is unique, controlled by a seed for reproducibility
- **Responsive sizing** — cathedrals scale to fit the canvas, from 40×30 up to 300×150
- **Gothic architecture elements**:
  - Twin towers with tapered spires and crosses
  - Pointed gothic arches for doors and windows
  - Ornate rose windows with petal patterns and radial spokes
  - Stained glass windows with colorful Unicode characters
  - Flying buttresses with pinnacles
  - Gargoyles perched on the façade
  - Clock faces on towers (showing random times)
  - Battlements/crenellations (sometimes)
  - Central spire (sometimes)
  - Double or single arched doors
  - Stone wall textures with course lines
  - Pitched roofs with ridge lines
- **ANSI color mode** (`--color`) — richly colored cathedrals in the terminal
- **Weather effects** (`--weather rain|snow|fog`) — atmospheric rain, snowfall, or fog
- **Crescent moon** — randomly appears in the sky during atmosphere mode
- **JSON metadata** (`--json`) — programmatically access seed, features, and dimensions
- **Save to file** (`--save FILE`) — write output to a file (overwrites existing file; appends for `--multi`)
- **Dimension validation** — helpful error messages for invalid sizes
- **Configurable**: set seed, canvas size, and generate multiple cathedrals at once
- **Reproducible**: use the same seed to recreate any cathedral exactly

## How to Install

No dependencies required — just Python 3.6+ with standard library:

```bash
# Clone or download, then run directly
python3 cathedral.py
```

## How to Run

```bash
# Random cathedral
python3 cathedral.py

# Reproducible cathedral with seed 42
python3 cathedral.py --seed 42

# Small cathedral (minimum size)
python3 cathedral.py --seed 42 --width 40 --height 30

# Larger cathedral
python3 cathedral.py --width 140 --height 60

# ANSI color output (for color-supporting terminals)
python3 cathedral.py --seed 42 --color

# With weather effects
python3 cathedral.py --seed 42 --weather rain
python3 cathedral.py --seed 42 --weather snow
python3 cathedral.py --seed 42 --weather fog

# Save to file
python3 cathedral.py --seed 42 --save cathedral.txt

# Output JSON metadata alongside the cathedral
python3 cathedral.py --seed 42 --json

# Generate 3 different cathedrals with sequential seeds
python3 cathedral.py --seed 100 --multi 3

# Combined: color + weather + save
python3 cathedral.py --seed 42 --color --weather snow --save output.txt

# Show version
python3 cathedral.py --version

# Show help
python3 cathedral.py --help
```

## Command-Line Options

| Flag | Description | Default |
|------|-------------|---------|
| `--seed SEED` | Random seed for reproducibility | random |
| `--width WIDTH` | Canvas width in characters (40–300) | 100 |
| `--height HEIGHT` | Canvas height in characters (30–150) | 50 |
| `--no-atmosphere` | Skip stars, moon, and ground texture | off |
| `--color` | Enable ANSI color output | off |
| `--weather` | Add weather: `rain`, `snow`, or `fog` | none |
| `--save FILE` | Save output to a file | stdout |
| `--json` | Print cathedral metadata as JSON | off |
| `--multi N` | Generate N cathedrals with sequential seeds | 1 |
| `--version` | Print version and exit | — |
| `--help` | Print usage help and exit | — |

## How It Works

The generator uses a layered construction approach:

1. **Foundation**: Stone steps at the base
2. **Main body**: Rectangular nave with textured walls and horizontal course lines
3. **Roof**: Pointed/pitched roof filled with shading
4. **Towers**: Two flanking towers with windows and spires
5. **Clock face** (optional): Circular clock with hour markers and hands on a tower
6. **Central spire** (optional): Taller spire rising from the roof peak
7. **Rose window** (optional): Circular stained glass window on the façade
8. **Side windows**: Pointed-arch stained glass windows arranged along the nave
9. **Door(s)**: Gothic arched entrance, optionally double doors
10. **Flying buttresses** (optional): Arched supports extending from the walls
11. **Gargoyles** (optional): Decorative creatures on the façade
12. **Atmosphere**: Random stars, crescent moon, and ground texture
13. **Weather** (optional): Rain, snow, or fog overlay

All element sizes (tower height, body height, roof height, spire height, window sizes) automatically scale down for small canvas sizes, ensuring cathedrals always render without crashes.

Each architectural element uses Unicode block characters (█▓▒░), box drawing characters (╔╗╚╝├┤┬┼), and decorative symbols (✝✿◆◇●○✦✧) to create rich visual detail.

## JSON Output

When using `--json`, the generator outputs structured metadata:

```json
{
  "seed": 42,
  "width": 100,
  "height": 50,
  "features": {
    "rose_window": true,
    "central_spire": true,
    "flying_buttresses": false,
    "gargoyles": false,
    "battlements": true,
    "clock": true,
    "double_door": false,
    "num_side_windows": 5,
    "door_width": 6
  },
  "weather": null
}
```

## Testing

Run the test suite:

```bash
python3 test_cathedral.py
```

Tests cover: canvas operations, drawing primitives, individual cathedral components, full generation, atmosphere/weather effects, dimension validation, CLI flags, save file behavior, small canvas sizes, and reproducibility.

## Changelog

### v1.2.0 — Bug fixes
- **Fixed crash on small canvas sizes** — heights below 30 (previously claimed minimum of 25) caused `ValueError: empty range in randrange`. Tower height, body height, roof height, spire height, window height, and door height now all scale dynamically to fit the available canvas space.
- **Raised minimum height from 25 to 30** — the true minimum that produces valid output is 30; the previous minimum of 25 always crashed.
- **Fixed header box misalignment** — the info line (`Size: ...`) was shorter than the top/bottom borders, leaving the right `║` unaligned. All header lines now use consistent `inner_w` formatting.
- **Fixed `--save` appending to existing files** — running `cathedral.py --save file.txt` twice would append a second cathedral to the same file. Now the first write truncates, and subsequent writes (within `--multi`) append.
- **Removed dead code** — eliminated the swapped `w, h = canvas.h, canvas.w` line in `add_rain()` that was immediately overwritten by the correct `w, h = canvas.w, canvas.h`.
- **Added tests** for small canvas sizes and save file truncation behavior.

## License

MIT