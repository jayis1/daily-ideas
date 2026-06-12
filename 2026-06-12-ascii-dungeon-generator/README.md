# 🏰 Procedural ASCII Dungeon Map Generator

Generate random dungeon maps with rooms, corridors, monsters, treasures, traps, and stairs — all rendered in beautiful ASCII art.

## Features

- **5 dungeon themes**: standard, crypt, inferno, forest, aquatic — each with unique wall/floor characters and monster sets
- **Difficulty levels 1–5**: controls monster density, trap frequency, and monster tier
- **Procedural generation**: BSP-like room placement with L-shaped corridors and extra loops for interesting layouts
- **Rich entities**: themed monsters (6 tiers), treasures with gold values, traps, water features, pillars, and doors
- **Reproducible seeds**: generate the same dungeon twice with `--seed`
- **Legend & stats**: optional detailed output showing all entities and dungeon metrics

## How to Run

```bash
python3 dungeon_generator.py
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `-W / --width` | 60 | Map width in characters |
| `-H / --height` | 30 | Map height in rows |
| `-r / --rooms` | 8 | Max number of rooms |
| `-t / --theme` | standard | Theme: `standard`, `crypt`, `inferno`, `forest`, `aquatic` |
| `-d / --difficulty` | 1 | Difficulty 1–5 |
| `-s / --seed` | random | Reproducible seed |
| `--legend` | off | Show entity legend |
| `--stats` | off | Show dungeon statistics |
| `--no-water` | off | Disable water puddles |
| `--no-pillars` | off | Disable pillars |
| `--no-traps` | off | Disable traps |
| `--no-doors` | off | Disable doors |

### Examples

```bash
# Default dungeon
python3 dungeon_generator.py

# Spooky crypt, hard difficulty
python3 dungeon_generator.py --theme crypt --difficulty 4 --legend

# Large forest dungeon with seed for reproducibility
python3 dungeon_generator.py -W 80 -H 40 -t forest -d 3 -s 42 --legend --stats

# Minimal dungeon — no traps, no water
python3 dungeon_generator.py --no-traps --no-water --no-pillars
```

## What It Does

The generator:

1. **Places rooms** randomly on a grid, ensuring no overlaps with margins
2. **Connects rooms** via L-shaped corridors using a minimum-spanning-tree approach, then adds extra corridors for loops
3. **Decorates rooms** with water puddles, pillars, and doors at corridor transitions
4. **Places stairs** — ▲ entrance in the first room, ▼ descent in the last
5. **Populates entities** — monsters scaled to difficulty, treasures with gold values, and hidden traps in corridors
6. **Renders** the final map with theme-appropriate characters, plus an optional legend and stats summary

## Output Sample

```
██████████████████████████████████████████████████████████████
████···███████████████████████████████·██████████████████████
████·▲·██████████████████████████████·██████████████████████
████···+++++++++++++++++++++++++++++++++++████████████████████
████·z·█·████████████████████████████·██████████████████████
███████·██·████████████████████████·██·█████████████████████
███████·██·████████████████████████·██·█████████████████████
```

Each character has meaning: walls, floors, corridors, doors, monsters, treasures, and traps — all explained in the legend output.