# 🏛️ Procedural Micro-Nation Generator

A command-line tool that generates complete fictional micro-nations — each with a unique ASCII flag, leader, national anthem, government, economy, culture, and diplomatic relations.

Every nation is procedurally created from seed data: name, motto, terrain, national animal, currency, cultural events, exports, and more. Generate a single nation or an entire geopolitical landscape with interconnected diplomatic ties.

## Features

- **Procedural nation generation** — names, mottos, governments, terrain, and more
- **ASCII flag rendering** — 10 flag patterns (tricolor, diagonal, cross, canton, chevron, saltire, barrulets, quarterly, bend) with 6 emblem types (star, diamond, circle, crescent, cross, triangle)
- **Colored output** — flags render with ANSI colors in the terminal; no-color mode uses distinct Unicode block characters
- **Diplomatic relations** — when generating multiple nations, each gets randomized diplomatic ties with strength bars
- **National leaders** — each nation gets a procedurally generated leader with title, name, and epithet
- **National anthems** — personality-matched opening lines for each nation's anthem
- **National holidays** — unique founding celebrations
- **Area & population density** — area is generated based on terrain type; density is auto-calculated
- **Seeded randomness** — use `--seed` for reproducible worlds
- **JSON output** — machine-readable output for pipeline use (`--json`)
- **Compact mode** — one-line summary per nation (`--compact`)
- **Comparison mode** — side-by-side comparison table (`--compare`)
- **File export** — save plaintext or JSON output to a file (`-o`)
- **List traits** — browse all available options (`--list-governments`, `--list-terrains`, etc.)
- **Version flag** — `--version` for version tracking

## Installation

No dependencies required — uses only the Python standard library.

```bash
# Clone and run
git clone https://github.com/your-username/daily-ideas.git
cd daily-ideas/2026-06-24-micro-nation-generator
chmod +x micro_nation.py
```

Requires Python 3.7+.

## Usage

```bash
# Generate 5 nations (default)
python3 micro_nation.py

# Generate 3 nations with a seed for reproducibility
python3 micro_nation.py -n 3 --seed mystic

# Generate a single nation
python3 micro_nation.py -n 1

# No-color mode (uses Unicode block chars for flag patterns)
python3 micro_nation.py --no-color

# Export as JSON
python3 micro_nation.py -n 5 --json

# Save output to a file
python3 micro_nation.py -n 10 --no-color -o nations.txt

# Show diplomatic relations between nations
python3 micro_nation.py -n 4 --diplomacy

# Compact one-line summary
python3 micro_nation.py -n 10 --compact

# Side-by-side comparison
python3 micro_nation.py -n 3 --compare

# Show version
python3 micro_nation.py --version

# List available trait options
python3 micro_nation.py --list-governments
python3 micro_nation.py --list-terrains
python3 micro_nation.py --list-animals
```

## Command-Line Options

| Flag | Description |
|------|-------------|
| `-n, --nations` | Number of nations to generate (default: 5) |
| `-s, --seed` | Random seed for reproducibility |
| `--no-color` | Disable ANSI color output |
| `--json` | Output as JSON |
| `--diplomacy` | Always show diplomatic relations |
| `--compact` | One-line summary per nation |
| `--compare` | Compare all generated nations side-by-side |
| `-o, --output` | Save output to a file |
| `--list-TRAIT` | List available options (governments, terrains, currencies, animals, mottos, exports, industries, cultures, personalities, patterns, colors, emblems) |
| `--version` | Show version and exit |

## Example Output

### Full Nation Display

```
  🏛️  FALCREST  🏛️
  "Strength in Silence"

  ┌────────────────────────────────┐
  │ ▓▓▓▓▓▓▓▓▓▓▓▓▓██▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │
  │ ▓▓▓▓▓▓░▓▓▓▓▓▓██▓▓▓▓▓▓▓▓▓▓▓▓▓ │
  │ ...                              │
  └────────────────────────────────┘

  🧠 Government: Noocracy
  Population: 5.5M
  Area: 12,450.0 km²
  Density: 442/km²
  Terrain: Crater caldera
  Capital: LittleBel
  Leader: Sage Aldric the Wise
  Currency: Obsidian Chip
  National Animal: Wind Stag
  Personality: Cunning
  Founded: 1861
  National Holiday: Founding Day

  Anthem: "The fox knows well which paths are blind,"

  Exports: deep-sea pearls, star-ash fertilizer, frost fruit preserves
  Industries: underwater viticulture, sky farming, gravity research
  Cultural Events:
    • Festival of Floating Lanterns
    • Tide Singer competitions
    • Echo Chamber meditation

  Diplomatic Relations:
    🧊 Caskeep: Frozen Relations [█████░░░░░] 51/100

  Seed: mystic-0
```

### Compact Mode

```
🏛️ Galdor | Technocratic Directorate | Pop: 234.5K | Area: 8.2K km² | Terrain: Mountainous Highlands | Founded: 1947
🏛️ Caskeep | Constitutional Monarchy | Pop: 1.2M | Area: 5.6K km² | Terrain: Coastal Peninsula | Founded: 1891
```

### Comparison Mode

```
  ═══ NATION COMPARISON ═══

  Attribute      │   Galdor   │   Caskeep  │
  ──────────────────────────────────────────────
  Government     │ ⚙️ Techn... │ 🏛️ Const... │
  Population     │   234.5K   │    1.2M    │
  ...
```

## What It Generates

Each micro-nation includes:

- **Name** — procedurally combined prefix+suffix (e.g., "Galdor", "Caskeep", "Nevton")
- **Motto** — inspirational national saying
- **Government** — from Constitutional Monarchy to Pirate Republic to Mage-ocracy
- **Population** — ranges from tiny (127) to substantial (8.5M)
- **Area** — terrain-appropriate land area (e.g., floating sky-islands: 10–200 km²)
- **Population Density** — auto-calculated from population and area
- **Terrain** — volcanic archipelago, floating sky-islands, underground cavern network, etc.
- **Capital** — procedurally named city
- **Leader** — procedurally generated leader with title, name, and epithet (e.g., "King Aldric the Bold")
- **Currency** — e.g., "Golden Shard", "Storm Crown", "Jade Slate"
- **National Animal** — fantasy creatures like Thunder Eagle, Crystal Fox, Tide Dragon
- **National Holiday** — founding celebrations
- **National Anthem** — personality-matched opening line
- **Exports** — 3 trade goods (enchanted timber, glow-fungus extract, etc.)
- **Industries** — 3 economic sectors (arcane engineering, cloud harvesting, etc.)
- **Cultural Events** — 3 festivals and traditions
- **Personality** — national temperament (stoic, whimsical, pragmatic, etc.)
- **Founding Year** — between 1800–2024
- **Flag** — a unique pattern+colors+emblem combination
- **Diplomatic Relations** — ties to other generated nations with type and strength

## Testing

```bash
# Run the full test suite (47 tests)
python3 -m pytest test_micro_nation.py -v

# Or with unittest
python3 -m unittest test_micro_nation -v
```

Tests cover RNG determinism, pick utility, nation generation (all fields, reproducibility, area validation), diplomatic relations (structure, no self-relations), flag rendering (all patterns, all emblems, color/no-color modes), formatting helpers, display output (compact, full, comparison), JSON serialization, CLI argument parsing, leader generation, anthem matching, and edge cases.

## Changelog

### v1.1.0 — Feature Release

**Added:**
- **National leaders** — each nation gets a leader with title, name, and epithet (e.g., "King Aldric the Bold")
- **National anthems** — personality-matched opening lines for each nation
- **National holidays** — unique founding celebrations per nation
- **Area & population density** — area generated based on terrain type; density auto-calculated
- **`--compact` mode** — one-line summary per nation for quick scanning
- **`--compare` mode** — side-by-side comparison table of generated nations
- **`--list-TRAIT` flags** — browse all available options (governments, terrains, animals, etc.)
- **`--version` flag** — show version number
- **Type hints** — added throughout the codebase
- **Docstrings** — comprehensive documentation on all public methods
- **47 unit tests** — full test coverage for generation, rendering, formatting, CLI, and edge cases
- **Input validation** — `--nations` must be ≥ 1; warning for > 50
- **UTF-8 encoding** — file output uses `encoding="utf-8"` for emoji support

**Improved:**
- `to_dict()` now includes `area_sq_km`, `population_density`, `leader`, `national_holiday`, `anthem_opening`
- Better variable naming and code organization
- `NationGenerator.generated_nations` is now properly typed as `List[MicroNation]`

## License

MIT