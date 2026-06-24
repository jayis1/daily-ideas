# 🏛️ Procedural Micro-Nation Generator

A command-line tool that generates complete fictional micro-nations — each with a unique ASCII flag, leader, national anthem, government, economy, culture, and diplomatic relations.

Every nation is procedurally created from seed data: name, motto, terrain, national animal, currency, cultural events, exports, and more. Generate a single nation or an entire geopolitical landscape with interconnected diplomatic ties.

## Features

- **Procedural nation generation** — names, mottos, governments, terrain, and more
- **ASCII flag rendering** — 10 flag patterns (tricolor, diagonal, cross, canton, chevron, saltire, barrulets, quarterly, bend) with 6 emblem types (star, diamond, circle, crescent, cross, triangle)
- **Colored output** — flags render with ANSI colors in the terminal; no-color mode uses distinct Unicode block characters
- **Diplomatic relations** — when generating multiple nations, each gets randomized diplomatic ties with strength bars
- **National leaders** — each nation gets a procedurally generated leader with title, name, and epithet (e.g., "King Aldric the Bold")
- **National anthems** — personality-matched opening lines for each nation
- **National holidays** — unique founding celebrations
- **Area & population density** — area is generated based on terrain type; population scales with area for realistic densities; density is auto-calculated
- **Seeded randomness** — use `--seed` for reproducible worlds
- **JSON output** — machine-readable output for pipeline use (`--json`)
- **Compact mode** — one-line summary per nation (`--compact`)
- **Comparison mode** — side-by-side comparison table (`--compare`)
- **File export** — save plaintext or JSON output to a file (`-o`); save messages go to stderr so JSON output stays clean for piping
- **List traits** — browse available options (`--list-governments`, `--list-terrains`, etc.)
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

# Save output to a file (save message goes to stderr, keeping stdout clean)
python3 micro_nation.py -n 10 --json -o nations.json

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
python3 micro_nation.py --list-currencies
python3 micro_nation.py --list-animals
```

## Command-Line Options

| Flag | Description |
|------|-------------|
| `-n, --nations` | Number of nations to generate (default: 5) |
| `-s, --seed` | Random seed for reproducibility |
| `--no-color` | Disable ANSI color output |
| `--json` | Output as JSON |
| `--diplomacy` | Always show diplomatic relations between nations |
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
  │ ▓▓▓▓▓▓▓▓▓▓▓██▓▓▓▓▓▓▓▓▓▓▓▓▓ │
  │ ▓▓▓▓▓▓░▓▓▓▓▓██▓▓▓▓▓▓▓▓▓▓▓▓ │
  │ ...                              │
  └────────────────────────────────┘

  🧠 Government: Noocracy
  Population: 5.5M
  Area: 12,450.0 km²
  Density: 442/km²
  Terrain: Crater caldera
  Capital: Mount Cor
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
- **Population** — scaled by terrain area for realistic densities (10–5000/km²)
- **Area** — terrain-appropriate land area (e.g., floating sky-islands: 10–200 km²)
- **Population Density** — auto-calculated from population and area
- **Terrain** — volcanic archipelago, floating sky-islands, underground cavern network, etc.
- **Capital** — procedurally named city with proper spacing (e.g., "New Haven", "Fort Cor")
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
# Run the full test suite (61 tests)
python3 -m pytest test_micro_nation.py -v

# Or with unittest
python3 -m unittest test_micro_nation -v
```

Tests cover RNG determinism (including integer seeds), pick utility, nation generation (all fields, reproducibility, area validation, realistic population density, capital name spacing), diplomatic relations (structure, no self-relations), flag rendering (all patterns, all emblems, color/no-color modes), formatting helpers (boundary cases for population/area), display output (compact, full, comparison), JSON serialization (including gov_icon and leader_title fields), CLI argument parsing (unique nations without seed, JSON file output purity, currency list format), leader generation, anthem matching, and edge cases (zero area, empty relations).

## Changelog

### v1.2.0 — Bug Fix Release

**Fixed:**
- **CRITICAL: All nations were identical without `--seed`** — The seed handling in `main()` produced `None` for every nation when no `--seed` was provided, causing `generate()` to create the same RNG from the same seed each iteration. Now uses unique time-based seeds per nation.
- **`make_rng()` crashed with integer seeds** — Calling `make_rng(42)` raised `AttributeError` because `.encode()` was called on an int. Now converts seeds to strings before encoding.
- **`format_population(999999)` showed "1000.0K" instead of "1.0M"** — Boundary values near unit transitions (999,999 → 1,000,000) were formatted as "1000.0K" instead of upgrading to "1.0M". Added overflow detection at the 999.95K boundary.
- **`format_area(999999)` showed "1000.0K km²" instead of "1.0M km²"** — Same boundary overflow bug as population formatting.
- **`--json --output` printed save message to stdout, corrupting JSON** — The "📄 Output saved" message was printed to stdout alongside JSON data, breaking `jq` and other pipe consumers. Now prints to stderr.
- **`--compact --output` file didn't include seed** — Compact file output omitted the seed line. Now includes it when `--seed` is provided.
- **`to_dict()` was missing `gov_icon` and `leader_title`** — JSON exports lacked the government emoji icon and the leader's title field. Both are now included.
- **Capital names had no space between prefix and root** — "Fort Bel" appeared as "FortBel", "New Haven" as "NewHaven". Added space between prefix and root.
- **Population density could reach millions/km²** — A nation on a 1 km² floating sea platform could have 8.5M people (8.5M/km²). Population now scales with terrain area, capped at realistic density limits (max ~5000/km² for city-states).
- **`--list-currencies` showed 280 misleading cartesian product items** — Listed every adjective×name combination as if they were all possible, but the generator actually picks one adjective and one name separately. Now shows the adjective and name lists separately.

**Added:**
- 14 new tests covering all bug fixes (integer seeds, unique nations, format boundaries, JSON purity, capital spacing, realistic density, currency list format)
- Version bumped to v1.2.0