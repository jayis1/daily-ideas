# 🔮 Spell Grimoire Generator

A CLI tool that generates unique fantasy RPG spell descriptions with arcane sigils, spell diagrams, incantations, and backstories. Perfect for Dungeon Masters, game designers, or anyone who wants procedural spell content.

## Features

- **8 schools of magic** — Abjuration, Conjuration, Divination, Enchantment, Evocation, Illusion, Necromancy, Transmutation
- **10 spell levels** — Cantrip (0) through 9th level
- **5 rarity tiers** — Common, Uncommon, Rare, Very Rare, Legendary (with weighted random selection)
- **Arcane sigils** — Procedurally generated runic symbols using elder futhark and geometric patterns
- **Spell diagrams** — Geometric spell circles with unique configurations per spell
- **Incantations** — School-themed verbal components with dramatic phrasing
- **Backstories** — Procedurally generated lore for each spell
- **Grammar-aware descriptions** — Singular/plural nouns handled correctly (e.g., "1 undead servant" vs "3 undead servants")
- **Correct ordinals** — "1st", "2nd", "3rd", "11th", "21st", etc.
- **Aligned box rendering** — Consistent 64-character width for all spell pages
- **Color and plaintext output** — ANSI color support with `--no-color` fallback
- **JSON export** — Structured output for integration with other tools (`--json`)
- **File output** — Write results to a file (`--output`)
- **Seed support** — Reproducible generation with `--seed`
- **Interactive mode** — Browse spells interactively
- **Spell list mode** — Compact table of generated spells (`--list`)
- **38+ unit tests** — Comprehensive test coverage

## Installation

```bash
# No external dependencies — uses only Python 3 standard library
cd 2026-06-22-spell-grimoire-generator
python3 grimoire.py --help
```

## Usage

### Generate a single spell

```bash
python3 grimoire.py
```

### Generate with specific school

```bash
python3 grimoire.py --school Necromancy
```

### Generate at a specific level

```bash
python3 grimoire.py --level 5
```

### Generate a specific rarity

```bash
python3 grimoire.py --rarity Legendary
```

### Generate multiple spells

```bash
python3 grimoire.py --count 5
```

### Generate a full grimoire (with header)

```bash
python3 grimoire.py --grimoire --count 3
```

### Reproducible output with seed

```bash
python3 grimoire.py --seed 42
```

### Plaintext (no ANSI colors)

```bash
python3 grimoire.py --no-color
```

### JSON output

```bash
python3 grimoire.py --json --count 3
```

### Spell list (compact table)

```bash
python3 grimoire.py --list 10
```

### Save to file

```bash
python3 grimoire.py --output spells.txt
```

### Show version

```bash
python3 grimoire.py --version
```

### Interactive mode

```bash
python3 grimoire.py --interactive
```

## Running Tests

```bash
python3 test_grimoire.py
```

## Example Output

```
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║           G R I M O I R E   O F   S P E L L S            ║
║                                                            ║
╠════════════════════════════════════════════════════════════╣
║ Necromancy — 3rd Level                                     ║
║ [Rare]                                                     ║
╠════════════════════════════════════════════════════════════╣
║ Twilight Grasp                                             ║
╠────────────────────────────────────────────────────────────╣
║ Casting Time: 1 hour                                       ║
║ Range: 60 feet                                             ║
║ Duration: 8 hours                                          ║
║ Components: V, S, M                                        ║
║   (a copper coin and ground stardust)                      ║
╠────────────────────────────────────────────────────────────╣
║                                                            ║
║           ○                                                ║
║         ··|··                                              ║
║       ·········                                            ║
║      ···◠ ☠ ◡···                                          ║
║       ·········                                            ║
║         ··|··                                              ║
║           ○                                                ║
║                                                            ║
╠────────────────────────────────────────────────────────────╣
║                                                            ║
║ Animates 1 undead servant for 8 hours, each with 29 HP.   ║
║                                                            ║
║ At Higher Levels. When cast using a spell slot of          ║
║ 4th level or higher, the duration doubles for each         ║
║ slot level above 3.                                        ║
║                                                            ║
╠────────────────────────────────────────────────────────────╣
║                                                            ║
║  "By dark beyond life, forsake and shine — let the        ║
║  world tremble!"                                           ║
║                                                            ║
╠────────────────────────────────────────════════════════════╣
║                                                            ║
║ This spell was first inscribed on the walls of the        ║
║ Sunken Temple of Gloomreach, discovered by the archmage   ║
║ Kaelen Stormborn during the Iron Collapse.                 ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

## Changelog

### v2.1.0 — Bug fixes
- **Fixed meta line alignment** — metadata lines (Casting Time, Range, etc.) were 1 character too short due to off-by-one in visible length calculation
- **Fixed incantation line alignment** — incantation lines were 1 character too short due to incorrect padding formula
- **Fixed material detail alignment** — material detail lines were 1 character too short
- **Fixed "At Higher Levels" overflow** — the first line of the "At Higher Levels" section could overflow the box boundary because word-wrapping didn't account for the "At Higher Levels. " prefix on the first line
- **Fixed grimoire header alignment** — header lines (title, empty lines, separator) were 2 characters too narrow (62 instead of 64); title is now centered programmatically
- **Fixed grammar** — descriptions like "1 undead servants" now correctly use singular form ("1 undead servant"); also fixed "1 creatures become", "1 allies", "1 hidden objects", "1 days"
- **Added `pluralize()` helper** — new function for grammar-correct singular/plural in descriptions
- **Added `first_line_width` parameter to `wrap_text()`** — enables shorter first line wrapping for the "At Higher Levels" prefix
- **Added 5 new tests** — box alignment (plaintext & color), grimoire header alignment, higher_levels wrapping, pluralize, wrap_text first_line_width, grammar singular count