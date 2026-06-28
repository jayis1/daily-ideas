# 🗺️ Procedural Treasure Map Generator

Generate unique, elaborate ASCII treasure maps with coastlines, terrain features, dotted trails, compass roses, sea monsters, pirate riddles, and X-marks-the-spot. Every map is procedurally generated — no two are alike!

## Features

- **Procedural Island Generation** — Fractal Brownian Motion noise creates organic coastlines, beaches, grasslands, forests, and mountains
- **Terrain Types** — Deep water, shallow water, sand beaches, grassland, forests, dense forests, mountains, and peaks
- **Treasure Trail** — A dotted path winds from a landing point (⚓) on the beach to the treasure (✕), with an anchor marker
- **Compass Rose** — A decorative N/S/E/W compass rose placed in open water
- **Sea Creatures** — Krakens, Leviathans, and Sea Serpents lurk in the deep
- **Named Landmarks** — "Dragon's Peak", "Whispering Forest", "Smuggler's Bay" and more are randomly placed
- **Pirate Riddles** — Generate cryptic verse clues pointing to the treasure
- **Map Legend** — Full symbol legend for all terrain types
- **Seedable RNG** — Use `--seed` to reproduce the same map
- **Unicode & ASCII modes** — Rich unicode symbols by default; `--no-unicode` for pure ASCII terminals
- **Batch generation** — Generate multiple maps with `--count`
- **Version flag** — `--version` shows the program version

## How to Install

No external dependencies needed — just Python 3.6+:

```bash
# Clone or download the script
# No pip install required!
```

## How to Run

```bash
# Generate a random treasure map
python3 treasure_map.py

# Generate a reproducible map with a specific seed
python3 treasure_map.py --seed 42

# Include a pirate riddle
python3 treasure_map.py --riddle

# Include a map legend
python3 treasure_map.py --legend

# Generate a larger map
python3 treasure_map.py --width 90 --height 40

# ASCII-only mode (for limited terminals)
python3 treasure_map.py --no-unicode

# Generate 3 different maps
python3 treasure_map.py --count 3

# Combine all options
python3 treasure_map.py --seed 42 --riddle --legend --width 80 --height 36

# Show version
python3 treasure_map.py --version

# Show help
python3 treasure_map.py --help
```

## Usage Examples

### Basic Map
```
python3 treasure_map.py
```
Outputs a bordered ASCII treasure map with terrain, a trail, landmarks, and treasure.

### Full Experience (Riddle + Legend)
```
python3 treasure_map.py --seed 42 --riddle --legend
```
Outputs the map plus a pirate riddle and a symbol legend.

### ASCII Mode
```
python3 treasure_map.py --no-unicode --seed 999
```
Same maps but using only standard ASCII characters, compatible with any terminal.

## How It Works

1. **Heightmap Generation**: Uses fractal Brownian motion (layered Perlin-like noise) to create a height field, with a radial falloff to produce island shapes
2. **Terrain Classification**: The heightmap is segmented into water/sand/grass/forest/mountain zones based on configurable thresholds
3. **Feature Placement**: The algorithm finds suitable locations for the treasure (inland, far from water), a landing point (beach adjacent to water, always distinct from the treasure), and overlays a winding trail between them
4. **Annotation**: Named landmarks, sea creatures, a compass rose, and ship are procedurally placed in appropriate terrain
5. **Collision Resolution**: Labels are automatically nudged to avoid overlapping, and the treasure X marker is always preserved even when labels pass nearby
6. **Rendering**: All layers are composited into a bordered ASCII display with optional riddle and legend

## Bugs Fixed (v1.1.0)

- **Landing on top of treasure**: The landing point could randomly coincide with the treasure X, producing a confusing trail of length 0. Now the landing always picks a location distinct from the treasure. (8/99 seeds were affected.)
- **Hardcoded Unicode symbols in ASCII mode**: `_add_coast_foam()`, `_add_lake_if_possible()`, and `_draw_trail()` used hardcoded `"~"` and `"·"` instead of `self.sym["water"]` and `self.sym["trail_dot"]`, leaking unicode into ASCII mode output.
- **Label overflow past grid width**: The "Here be treasure!" label (17 chars) was placed using a hardcoded offset of 15, causing it to extend past the grid boundary on ~40% of seeds. Labels are now clamped to grid bounds.
- **Annotations overwriting the treasure X**: Labels overlapping the treasure position would erase the ✕ marker. The render now protects the treasure cell and restores it after all annotations are drawn. (7/99 seeds were affected.)
- **Annotations overlapping each other**: Multiple labels on the same row would overwrite each other. A collision resolution system now nudges overlapping labels to different rows. (31/99 seeds had overlaps.)
- **Ship label not bounded**: The `_add_ship()` label placement could extend past the grid edge. Now uses `_add_annotation()` for proper bounds checking.
- **Unicode in ASCII mode headers**: The title box, riddle box, and legend box used Unicode box-drawing characters even in `--no-unicode` mode. Now uses ASCII `+`/`-`/`|` equivalents.
- **Missing `--version` flag**: Added `--version` flag showing program version.
- **Trail dot inconsistency**: The alternate trail dots (odd-indexed) used hardcoded `"·"` instead of `self.sym["trail_dot"]`, producing inconsistent rendering in ASCII mode.

## Testing

Run the test suite:

```bash
python3 test_treasure_map.py
```

The test suite covers:
- Basic construction and grid dimensions
- Seed reproducibility
- Unicode vs ASCII mode symbol correctness
- Treasure placement on land
- Landing distinct from treasure
- Label overflow bounds checking
- Annotation collision resolution
- Treasure X preservation under annotations
- Hardcoded symbol consistency in code
- Edge case map sizes (tiny, extreme aspect ratios)
- All-water and all-land maps
- Riddle and legend generation
- CLI flags (--version, --help, --seed, --riddle, --legend, --no-unicode)