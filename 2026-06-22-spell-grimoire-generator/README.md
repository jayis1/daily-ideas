# Spell Grimoire Generator v3.1.0

A procedurally-generated D&D 5e-style spell grimoire creator. Generate unique spells with names, descriptions, incantations, sigils, mana costs, tags, and synergies — all from random seeds.

## Features

- **Procedural Spell Generation** — Every spell has a unique name, school, level, description, casting time, range, duration, components, incantation, sigil, diagram, and lore
- **8 Schools of Magic** — Abjuration, Conjuration, Divination, Enchantment, Evocation, Illusion, Necromancy, Transmutation
- **9 Spell Levels** — Cantrip (0) through 9th level, with rarity scaling
- **Mana Cost System** — Calculated from level, school, rarity, casting time, and duration
- **Spell Tags** — Thematic tags based on school, level, rarity, and damage type
- **Spell Synergies** — Detect pairs of spells from different schools that complement each other
- **Side-by-Side Comparison** — Render two spells in parallel columns
- **Grimoire Mode** — Generate a full 5-spell grimoire with decorative header
- **Spell Lists** — Tabular overview with rarity, level, mana, school, and name
- **Interactive Mode** — Menu-driven spell generation and exploration
- **Save/Load** — Persist spells to JSON files and recall them later
- **Markdown Export** — Clean Markdown output with headers, metadata, tags, and lore
- **Colorful Terminal Output** — ANSI-colored grimoire pages with box-drawing characters
- **Deterministic Seeds** — Use `--seed` for reproducible output

## Installation

```bash
# Clone the repository
git clone <repo-url> ~/daily-ideas
cd ~/daily-ideas/2026-06-22-spell-grimoire-generator

# No external dependencies required — uses only Python standard library
python3 grimoire.py --help
```

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
python3 grimoire.py --rarity Rare
```

### Output Formats

```bash
# JSON output
python3 grimoire.py --json

# JSON with multiple spells
python3 grimoire.py --json --count 5

# Markdown output
python3 grimoire.py --markdown

# Write to file
python3 grimoire.py --output grimoire.txt

# No color (plain text)
python3 grimoire.py --no-color
```

### Grimoire & Lists

```bash
# Generate a 5-spell grimoire
python3 grimoire --grimoire

# Generate a school-specific grimoire
python3 grimoire --grimoire --school Evocation

# Generate a spell list (tabular)
python3 grimoire --list 10

# School-filtered list
python3 grimoire --list 5 --school Abjuration
```

### Synergies & Comparison

```bash
# Find synergies between 5 spells
python3 grimoire.py --synergies 5

# Compare two spells side-by-side
python3 grimoire.py --compare

# Compare with a specific school
python3 grimoire.py --compare --school Necromancy
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
```

### Interactive Mode

```bash
python3 grimoire.py --interactive
```

Interactive menu options:
1. Generate random spell
2. Generate spell from specific school
3. Generate spell at specific level
4. Generate spell with specific rarity
5. Show spell list
6. Show spell synergies
7. Compare two spells
8. Find synergies
9. View generation history
s. Save spells to file
l. Load spells from file
q. Quit

## Running Tests

```bash
python3 -m pytest test_grimoire.py -v
```

The test suite includes 98 tests covering spell generation, mana costs, tags, synergies, save/load, rendering, grammar, seed determinism, and CLI flags.

## Bug Fixes (v3.1.0)

- **Grammar: "for Instantaneous"** — Effect descriptions no longer produce phrases like "for Instantaneous" or "for Until dispelled". Duration phrases are now grammatically correct (e.g., empty for Instantaneous, "until dispelled" for Until dispelled, "for up to X" for Concentration durations).
- **Grammar: singular "each with"** — Necromancy spells with 1 undead servant now say "with X HP" instead of the incorrect ", each with X HP".
- **Grammar: Divination templates** — "For {duration}" templates that produced "For Instantaneous" now use `{duration_phrase}` to avoid grammatically incorrect phrasing.
- **Seed determinism** — The `_generated_names` global set is now reset when `--seed` is used, ensuring the same seed always produces the same spells across separate runs.
- **`--grimoire` with `--save`** — Grimoire mode now properly collects generated spells and saves them to JSON files.
- **`--list` with `--save`** — List mode now properly collects generated spells and saves them to JSON files.
- **`format_duration_phrase_cap`** — Fixed to correctly capitalize the first letter (not the leading space) in capitalized duration phrases.

## Project Structure

```
2026-06-22-spell-grimoire-generator/
├── grimoire.py          # Main script (spell generator, renderer, CLI)
├── test_grimoire.py     # Test suite (98 tests)
└── README.md            # This file
```

## License

MIT