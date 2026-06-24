# Procedural Micro-Nation Generator

A command-line tool that generates complete fictional micro-nations — each with a unique ASCII flag, government, economy, culture, and diplomatic relations.

Every nation is procedurally created from seed data: name, motto, terrain, national animal, currency, cultural events, exports, and more. Generate a single nation or an entire geopolitical landscape with interconnected diplomatic ties.

## Features

- **Procedural nation generation** — names, mottos, governments, terrain, and more
- **ASCII flag rendering** — 10 flag patterns (tricolor, diagonal, cross, canton, chevron, saltire, etc.) with 6 emblem types (star, diamond, circle, crescent, cross, triangle)
- **Colored output** — flags render with ANSI colors in the terminal; no-color mode uses distinct Unicode block characters
- **Diplomatic relations** — when generating multiple nations, each gets randomized diplomatic ties with strength bars
- **Seeded randomness** — use `--seed` for reproducible worlds
- **JSON output** — machine-readable output for pipeline use
- **File export** — save plaintext or JSON output to a file

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
```

## Command-Line Options

| Flag | Description |
|------|-------------|
| `-n, --nations` | Number of nations to generate (default: 5) |
| `-s, --seed` | Random seed for reproducibility |
| `--no-color` | Disable ANSI color output |
| `--json` | Output as JSON |
| `--diplomacy` | Always show diplomatic relations |
| `-o, --output` | Save output to a file |

## Example Output

```
🧠  FALCREST  🧠

  ┌────────────────────────────────┐
  │ ▓▓▓▓▓▓▓▓▓▓▓▓▓██▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │
  │ ▓▓▓▓▓▓░▓▓▓▓▓▓██▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │
  │ ▓▓▓▓▓░░▓▓▓▓▓▓██▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │
  │ ...                              │
  └────────────────────────────────┘

  🧠 Government: Noocracy
  Population: 5.5M
  Terrain: Crater caldera
  Capital: LittleBel
  Currency: Obsidian Chip
  National Animal: Wind Stag
  Personality: Cunning
  Founded: 1861

  Exports: deep-sea pearls, star-ash fertilizer, frost fruit preserves
  Industries: underwater viticulture, sky farming, gravity research
  Cultural Events:
    • Festival of Floating Lanterns
    • Tide Singer competitions
    • Echo Chamber meditation

  Diplomatic Relations:
    🧊 Caskeep: Frozen Relations [█████░░░░░] 51/100
```

## What It Generates

Each micro-nation includes:

- **Name** — procedurally combined prefix+suffix (e.g., "Galdor", "Caskeep", "Nevton")
- **Motto** — inspirational national saying
- **Government** — from Constitutional Monarchy to Pirate Republic to Mage-ocracy
- **Population** — ranges from tiny (127) to substantial (8.5M)
- **Terrain** — volcanic archipelago, floating sky-islands, underground cavern network, etc.
- **Capital** — procedurally named city
- **Currency** — e.g., "Golden Shard", "Storm Crown", "Jade Slate"
- **National Animal** — fantasy creatures like Thunder Eagle, Crystal Fox, Tide Dragon
- **Exports** — 3 trade goods (enchanted timber, glow-fungus extract, etc.)
- **Industries** — 3 economic sectors (arcane engineering, cloud harvesting, etc.)
- **Cultural Events** — 3 festivals and traditions
- **Personality** — national temperament (stoic, whimsical, pragmatic, etc.)
- **Founding Year** — between 1800–2024
- **Flag** — a unique pattern+colors+emblem combination
- **Diplomatic Relations** — ties to other generated nations with type and strength

## License

MIT