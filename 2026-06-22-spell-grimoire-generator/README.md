# Spell Grimoire Generator

**Version 4.0.1** — A procedural D&D 5e–style spell generator that creates unique spells with names, descriptions, stats, sigils, diagrams, and incantations. Outputs in color terminal, Markdown, JSON, or HTML.

## Features

- **Procedural Spell Generation** — Creates unique spells with names, schools, levels, rarities, mana costs, casting times, ranges, durations, descriptions, lore, tags, sigils, diagrams, and incantations
- **8 Magic Schools** — Abjuration, Conjuration, Divination, Enchantment, Evocation, Illusion, Necromancy, Transmutation — each with unique templates, creatures, and effects
- **10 Spell Levels** — Cantrip through 9th level, with appropriate stats scaling
- **5 Rarity Tiers** — Common, Uncommon, Rare, Very Rare, Legendary — affecting stats and scroll values
- **Scroll GP Values** — Every spell includes a gold-piece value for purchasing spell scrolls, calculated from level and rarity
- **Spell Conflict Detection** — `--conflicts N` identifies pairs of spells whose schools clash (e.g., Evocation ↔ Illusion, Necromancy ↔ Abjuration)
- **Statistical Analysis** — `--stats N` shows breakdown of N spells by school, level, rarity, plus average/total mana cost and scroll value
- **Grimoire Mode** — `--grimoire` generates a beautifully formatted multi-spell grimoire with borders and headers
- **Spell List Mode** — `--list N` generates a compact table with Rarity, Level, Mana, Scroll value, School, and Spell Name columns
- **Side-by-Side Comparison** — `--compare` shows two spells side by side
- **Synergy Detection** — `--synergies` finds and describes synergies between spells
- **Markdown Export** — `--markdown` outputs formatted Markdown with headers, tables, and spell details
- **JSON Export** — `--json` outputs structured JSON data for programmatic use
- **HTML Export** — `--html` generates a standalone dark-fantasy-themed HTML document with school-colored badges
- **Save & Load** — `--save` writes spells to JSON file; `--load` reads them back
- **Deterministic Seeding** — `--seed N` produces reproducible results
- **Color Output** — Rich ANSI terminal colors with school-themed palettes (disable with `--no-color`)
- **Interactive Mode** — Run without flags for an interactive menu

## Installation

```bash
# No dependencies needed — uses only Python standard library
cd 2026-06-22-spell-grimoire-generator
python3 grimoire.py --help
```

## Usage

### Basic

```bash
# Generate a random spell
python3 grimoire.py

# Generate with a specific seed for reproducibility
python3 grimoire.py --seed 42

# Generate a specific school
python3 grimoire.py --school Evocation

# Generate a specific level
python3 grimoire.py --level 5

# Generate a specific rarity
python3 grimoire.py --rarity Legendary

# Generate multiple spells
python3 grimoire.py --count 10
```

### Output Formats

```bash
# JSON output
python3 grimoire.py --json --seed 42

# Markdown output
python3 grimoire.py --markdown --seed 42

# HTML output
python3 grimoire.py --html --count 3

# Save to file
python3 grimoire.py --json --seed 42 --output spells.json

# Plain text (no ANSI colors)
python3 grimoire.py --no-color --seed 42
```

### Grimoire Mode

```bash
# Generate a 5-spell grimoire
python3 grimoire.py --grimoire --seed 42

# Filter by school
python3 grimoire.py --grimoire --school Necromancy --seed 42

# Filter by level
python3 grimoire.py --grimoire --level 5 --seed 42

# Filter by rarity
python3 grimoire.py --grimoire --rarity Legendary --seed 42
```

### Spell List Mode

```bash
# Generate a table of 10 spells
python3 grimoire.py --list 10

# List with filters
python3 grimoire.py --list 5 --school Evocation --level 3 --seed 42
python3 grimoire.py --list 3 --rarity Rare --seed 42
```

### Analysis

```bash
# Conflict detection
python3 grimoire.py --conflicts 10 --seed 42

# Statistical analysis
python3 grimoire.py --stats 20 --seed 42

# Side-by-side comparison
python3 grimoire.py --compare --seed 42
```

### Saving & Loading

```bash
# Save spells to JSON
python3 grimoire.py --count 5 --json --save my_spells.json --seed 42

# Load and display saved spells
python3 grimoire.py --load my_spells.json
```

## Running Tests

```bash
python3 -m pytest test_grimoire.py -v
```

135 tests covering spell generation, rarity, mana costs, tags, synergies, save/load, rendering, Markdown/JSON/HTML export, CLI flags, scroll values, conflicts, stats, and bug-fix regressions.

## Bug Fixes in v4.0.1

- **CLI `--list` missing Scroll column** — The `--list` CLI mode had a different column layout than `generate_spell_list()`, omitting the Scroll (gold piece) column. Fixed to include scroll values, matching the function output.
- **CLI `--grimoire` ignoring `--level` and `--rarity`** — The `--grimoire` mode only passed `school` to `generate_spell()`, silently ignoring `--level` and `--rarity` flags. Both are now forwarded correctly.
- **CLI `--list` ignoring `--level` and `--rarity`** — The `--list` mode had the same issue. Both flags are now forwarded to `generate_spell()`.
- **`generate_grimoire()` and `generate_spell_list()` missing `level`/`rarity` parameters** — Both functions only accepted `school` for filtering. Added `level` and `rarity` parameters to match the CLI behavior and `generate_spell()`'s signature.

## Changelog

- **v4.0.1** — Bug fixes: added Scroll column to CLI `--list`, forwarded `--level`/`--rarity` in `--grimoire` and `--list` CLI modes, added `level`/`rarity` parameters to `generate_grimoire()` and `generate_spell_list()`, added 11 regression tests
- **v4.0.0** — Added scroll GP values, spell conflict detection, statistical analysis, HTML export
- **v1.0.0** — Initial release with procedural spell generation, Markdown/JSON export, grimoire mode, CLI