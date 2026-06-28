# 🗺️ Procedural Treasure Map Generator

Generate unique, elaborate ASCII treasure maps with coastlines, terrain features, dotted trails, compass roses, sea monsters, pirate riddles, and X-marks-the-spot. Every map is procedurally generated — no two are alike!

## Features

- **Procedural Island Generation** — Fractal Brownian Motion noise creates organic coastlines, beaches, grasslands, forests, and mountains
- **Terrain Types** — Deep water, shallow water, sand beaches, grassland, forests, dense forests, mountains, and peaks
- **Treasure Trail** — A dotted path winds from a landing point (⚓) on the beach to the treasure (✕), complete with an anchor marker
- **Compass Rose** — A decorative N/S/E/W compass rose placed in open water
- **Sea Creatures** — Krakens, Leviathans, and Sea Serpents lurk in the deep
- **Named Landmarks** — "Dragon's Peak", "Whispering Forest", "Smuggler's Bay" and more are randomly placed
- **Pirate Riddles** — Generate cryptic verse clues pointing to the treasure
- **Map Legend** — Full symbol legend for all terrain types
- **Seedable RNG** — Use `--seed` to reproduce the same map
- **Unicode & ASCII modes** — Rich unicode symbols by default; `--no-unicode` for terminals that need plain ASCII
- **Batch generation** — Generate multiple maps with `--count`

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
3. **Feature Placement**: The algorithm finds suitable locations for the treasure (inland, far from water), a landing point (beach adjacent to water), and overlays a winding trail between them
4. **Annotation**: Named landmarks, sea creatures, a compass rose, and ship are procedurally placed in appropriate terrain
5. **Rendering**: All layers are composited into a bordered ASCII display with optional riddle and legend

## What It Does

Each run produces a unique treasure map that tells a story: a ship arrives at anchor, follows a dotted trail past named landmarks and through varied terrain, to reach the buried treasure. The "Here be dragons" marginalia and sea creature labels add authentic cartographic flavor. Use it for:

- RPG game props and handouts
- Creative writing prompts
- Terminal art fun
- Procedural content inspiration
- Coding challenge demonstrations (noise functions, pathfinding, procedural generation)