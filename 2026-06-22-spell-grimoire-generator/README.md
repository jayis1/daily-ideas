# Spell Grimoire Generator v4.0.0

A procedurally-generated D&D 5e-style spell grimoire creator. Generate unique spells with names, descriptions, incantations, sigils, mana costs, scroll values, tags, synergies, and conflicts — all from random seeds.

## Features

### Core Generation
- **Procedural Spell Generation** — Every spell has a unique name, school, level, description, casting time, range, duration, components, incantation, sigil, diagram, and lore
- **8 Schools of Magic** — Abjuration, Conjuration, Divination, Enchantment, Evocation, Illusion, Necromancy, Transmutation
- **9 Spell Levels** — Cantrip (0) through 9th level, with rarity scaling
- **5 Rarity Tiers** — Common, Uncommon, Rare, Very Rare, Legendary (with weighted random selection)

### Calculations & Metadata
- **Mana Cost System** — Calculated from level, school, rarity, casting time, and duration
- **Scroll GP Values** — D&D-style gold piece pricing for spell scrolls, based on level and rarity
- **Spell Tags** — Thematic tags based on school, level, rarity, and damage type
- **Spell Synergies** — Detect pairs of spells from different schools that complement each other
- **Spell Conflicts** — Detect pairs of spells whose schools clash or interfere with each other

### Output Formats
- **Terminal Output** — ANSI-colored grimoire pages with box-drawing characters and Unicode sigils
- **Markdown Export** — Clean Markdown output with headers, metadata, tags, and lore (`--markdown`)
- **JSON Export** — Structured JSON output for programmatic use (`--json`)
- **HTML Export** — Standalone styled HTML document with dark theme (`--html`)
- **Plaintext** — Stripped of ANSI codes (`--no-color`)

### Display Modes
- **Single Spell** — Generate and display one spell
- **Grimoire Mode** — Generate a full 5-spell grimoire with decorative header (`--grimoire`)
- **Spell Lists** — Tabular overview with rarity, level, mana, scroll value, school, and name (`--list N`)
- **Side-by-Side Comparison** — Render two spells in parallel columns (`--compare`)
- **Synergies** — Find complementary school pairings among N spells (`--synergies N`)
- **Conflicts** — Find incompatible school pairings among N spells (`--conflicts N`)
- **Statistics** — Aggregate analysis of generated spells (`--stats N`)
- **Interactive Mode** — Menu-driven spell generation and exploration (`--interactive`)

### Persistence
- **Save/Load** — Persist spells to JSON files and recall them later
- **Deterministic Seeds** — Use `--seed` for reproducible output

## Installation

```bash
# No external dependencies — uses only Python standard library
git clone <repo-url> ~/daily-ideas
cd ~/daily-ideas/2026-06-22-spell-grimoire-generator

python3 grimoire.py --help
```

Requires Python 3.7+.

## Usage

### Basic Spell Generation

```bash
# Generate a random spell
python3 grimoire.py

# Generate 3 spells
python3 grimoire.py --count 3

# Generate with a specific seed (deterministic)
python3 grimoire.py --seed 42

# Generate a spell from a specific school
python3 grimoire.py --school Necromancy

# Generate a spell at a specific level (0-9)
python3 grimoire.py --level 5

# Generate with a specific rarity
python3 grimoire.py --rarity Legendary
```

### Output Formats

```bash
# JSON output
python3 grimoire.py --json

# JSON with multiple spells
python3 grimoire.py --json --count 5

# Markdown output
python3 grimoire.py --markdown

# HTML output (standalone dark-themed page)
python3 grimoire.py --html

# HTML with multiple spells
python3 grimoire.py --html --count 3 -o grimoire.html

# Write to file
python3 grimoire.py --output grimoire.txt

# No color (plain text)
python3 grimoire.py --no-color
```

### Grimoire & Lists

```bash
# Generate a 5-spell grimoire
python3 grimoire.py --grimoire

# Generate a school-specific grimoire
python3 grimoire.py --grimoire --school Evocation

# Generate a spell list (tabular)
python3 grimoire.py --list 10

# School-filtered list
python3 grimoire.py --list 5 --school Abjuration
```

### Synergies, Conflicts & Comparison

```bash
# Find synergies between 5 spells
python3 grimoire.py --synergies 5

# Find conflicts between 5 spells
python3 grimoire.py --conflicts 5

# Compare two spells side-by-side
python3 grimoire.py --compare

# Compare with a specific school
python3 grimoire.py --compare --school Necromancy
```

### Statistics

```bash
# Show statistics for 20 random spells
python3 grimoire.py --stats 20

# Statistics for a specific school
python3 grimoire.py --stats 20 --school Evocation

# Statistics for high-level spells
python3 grimoire.py --stats 15 --level 7
```

### Save & Load

```bash
# Save generated spells to a JSON file
python3 grimoire.py --count 5 --save spells.json

# Save from grimoire mode
python3 grimoire.py --grimoire --save grimoire_spells.json

# Save from list mode
python3 grimoire.py --list 3 --save list_spells.json

# Load and display saved spells
python3 grimoire.py --load spells.json

# Load and export as HTML
python3 grimoire.py --load spells.json --html -o loaded.html
```

### Interactive Mode

```bash
python3 grimoire.py --interactive
```

Interactive menu options:
1. Generate random spell
2. Generate spell from specific school
3. Generate a grimoire (5 spells)
4. Generate a spell list (10 spells)
5. Browse spells by level
6. Browse spells by rarity
7. Compare two spells side-by-side
8. Find synergies in recent spells
9. View spell history
c. Find conflicts in recent spells
t. View statistics
s. Save spells to file
l. Load spells from file
q. Quit

## Running Tests

```bash
python3 -m pytest test_grimoire.py -v
```

The test suite includes 124 tests covering spell generation, mana costs, scroll values, tags, synergies, conflicts, stats, HTML export, save/load, rendering, grammar, seed determinism, and all CLI flags.

## What's New in v4.0.0

### New Features
- **Scroll GP Values** — Every spell now includes a gold-piece value for purchasing spell scrolls, based on D&D 5e-style pricing (level × base price × rarity multiplier). Displayed in grimoire pages, spell lists, Markdown output, and JSON output.
- **Spell Conflicts** — `--conflicts N` flag and interactive option `c` detect pairs of spells whose schools clash (e.g., Evocation vs. Illusion, Necromancy vs. Abjuration), with 8 conflict pairings and descriptive explanations.
- **Statistical Analysis** — `--stats N` flag and interactive option `t` display a breakdown of N spells by school, level, rarity, plus average/total mana cost and scroll value metrics.
- **HTML Export** — `--html` flag generates a fully styled standalone HTML document with a dark fantasy theme, school-colored badges, and proper structure. Works with `--count`, `--output`, and `--load`.
- **Interactive Mode** — New options `c` (conflicts) and `t` (statistics) added to the interactive menu. Spell info lines now show scroll values.

### Improvements
- Scroll value column added to spell list output (`--list`)
- Markdown export now includes scroll value in the header
- Save/load now properly round-trips the `scroll_value` field (backward-compatible with old files)
- Version bumped to 4.0.0

## Project Structure

```
2026-06-22-spell-grimoire-generator/
├── grimoire.py          # Main script (spell generator, renderer, CLI)
├── test_grimoire.py     # Test suite (124 tests)
└── README.md            # This file
```

## License

MIT