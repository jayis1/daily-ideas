# 🗺️ Procedural Treasure Map Generator

Generate unique, elaborate ASCII treasure maps with coastlines, terrain features, dotted trails, compass roses, sea monsters, pirate riddles, and X-marks-the-spot. Every map is procedurally generated — no two are alike!

## Features

- **Procedural Island Generation** — Fractal Brownian Motion noise creates organic coastlines, beaches, grasslands, forests, mountains, and peaks
- **Terrain Types** — Deep water, shallow water, sand beaches, grassland, forests, dense forests, mountains, peaks, swamps, volcanoes, and lava flows
- **Treasure Trail** — A dotted path winds from a landing point (⚓) on the beach to the treasure (✕), with an anchor marker and distance estimate
- **Compass Rose** — A decorative N/S/E/W compass rose placed in open water
- **Sea Creatures** — Krakens, Leviathans, and Sea Serpents lurk in the deep
- **Named Landmarks** — "Dragon's Peak", "Whispering Forest", "Smuggler's Bay", and more are randomly placed on appropriate terrain
- **Pirate Riddles** — Generate context-aware riddle clues that reference actual landmarks on your map
- **Volcanoes** — Dramatic volcanic features with lava flows and danger markers appear on elevated terrain
- **Swamps** — Marshy transition zones near water add atmosphere and danger
- **Danger Markers** — Skull and cross markers near volcanoes and swamps
- **Map Legend** — Full symbol legend for all terrain types including swamp, volcano, and lava
- **Terrain Statistics** — Show a percentage breakdown of all terrain types with a visual bar chart (`--stats`)
- **Difficulty Presets** — Choose `easy` (big islands), `normal` (balanced), or `hard` (tiny atolls) to control map challenge
- **Seedable RNG** — Use `--seed` to reproduce the same map
- **Unicode & ASCII modes** — Rich unicode symbols by default; `--no-unicode` for pure ASCII terminals
- **Save to file** — Use `--save FILE` to write output to a file
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

# Include a pirate riddle (context-aware!)
python3 treasure_map.py --riddle

# Include a map legend
python3 treasure_map.py --legend

# Show terrain statistics
python3 treasure_map.py --stats

# Generate an easy map (bigger islands)
python3 treasure_map.py --difficulty easy

# Generate a hard map (tiny atolls, mostly water)
python3 treasure_map.py --difficulty hard

# Generate a larger map
python3 treasure_map.py --width 90 --height 40

# ASCII-only mode (for limited terminals)
python3 treasure_map.py --no-unicode

# Save output to a file
python3 treasure_map.py --seed 42 --save my_map.txt

# Generate 3 different maps
python3 treasure_map.py --count 3

# Combine all options
python3 treasure_map.py --seed 42 --riddle --legend --stats --width 80 --height 36 --difficulty easy

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
Outputs a bordered ASCII treasure map with terrain, a trail, landmarks, and treasure. Shows estimated distance from landing to treasure.

### Full Experience (Riddle + Legend + Stats)
```
python3 treasure_map.py --seed 42 --riddle --legend --stats
```
Outputs the map plus a context-aware pirate riddle (referencing actual landmarks on the map), a symbol legend, terrain statistics, and a distance estimate.

### Difficulty Modes
```
python3 treasure_map.py --difficulty easy --riddle
python3 treasure_map.py --difficulty hard --stats
```
- **Easy** — Larger islands with more land to explore
- **Normal** — Balanced island with mixed terrain (default)
- **Hard** — Tiny atoll surrounded by treacherous waters

### Save to File
```
python3 treasure_map.py --seed 42 --save treasure.txt
```
Writes the complete output to `treasure.txt` instead of printing to stdout.

### ASCII Mode
```
python3 treasure_map.py --no-unicode --seed 999
```
Same maps but using only standard ASCII characters, compatible with any terminal.

## How It Works

1. **Heightmap Generation**: Uses fractal Brownian motion (layered Perlin-like noise) to create a height field, with a radial falloff to produce island shapes
2. **Terrain Classification**: The heightmap is segmented into water/sand/grass/forest/mountain zones based on configurable thresholds, with difficulty presets adjusting these thresholds
3. **Feature Placement**: The algorithm finds suitable locations for the treasure (inland, far from water), a landing point (beach adjacent to water, always distinct from the treasure), and overlays a winding trail between them
4. **Special Features**: Inland lakes, swamps, and volcanoes are conditionally generated based on terrain suitability and random chance
5. **Annotation**: Named landmarks, sea creatures, a compass rose, and ship are procedurally placed in appropriate terrain
6. **Collision Resolution**: Labels are automatically nudged to avoid overlapping, and the treasure X marker is always preserved even when labels pass nearby
7. **Context-Aware Riddles**: The riddle system checks for actual landmarks on the map and generates clues that reference them by name, including distance hints
8. **Rendering**: All layers are composited into a bordered ASCII display with optional riddle, legend, and statistics

## Testing

Run the test suite:

```bash
python3 test_treasure_map.py
```

The test suite covers 101 tests including:
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
- Context-aware riddles referencing landmarks
- Difficulty presets (easy/normal/hard)
- Terrain statistics (percentage sums to 100%)
- Trail distance calculation
- Swamp and volcano generation
- Danger markers
- CLI flags (--version, --help, --seed, --riddle, --legend, --no-unicode, --difficulty, --stats, --save)

## Version History

### v1.2.0
- **New: Difficulty presets** — `--difficulty easy|normal|hard` controls island size and terrain distribution
- **New: Volcanoes** — Volcanic features with lava flows appear on elevated terrain, with danger markers (☠)
- **New: Swamps** — Marshy transition zones near water, with their own landmarks
- **New: Terrain statistics** — `--stats` shows a percentage breakdown with visual bar chart
- **New: Distance estimate** — Shows approximate paces from landing to treasure
- **New: Context-aware riddles** — Riddles now reference actual landmarks on the map and include distance hints
- **New: `--save FILE` flag** — Save output to a file instead of stdout
- **New: Danger markers** — Skull markers near volcanoes and swamps
- **New: Enhanced legend** — Now includes swamp, volcano, and lava symbols
- **Improved: CLI validation** — Warns on oversized maps, errors on too-small dimensions
- **Improved: Trail rendering** — Alternating dash/dot pattern for better visual clarity
- **Improved: Volcano placement** — Falls back to mountains and dense forests if no peaks exist
- **Improved: Stats rounding** — Percentages now sum to exactly 100%

### v1.1.0
- Fixed: Landing point coinciding with treasure
- Fixed: Hardcoded Unicode symbols in ASCII mode
- Fixed: Label overflow past grid width
- Fixed: Annotations overwriting the treasure X
- Fixed: Annotation collision resolution
- Fixed: Ship label not bounded
- Fixed: Unicode in ASCII mode headers
- Added: `--version` flag
- Fixed: Trail dot inconsistency