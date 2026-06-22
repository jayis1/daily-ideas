# 🔮 Spell Grimoire Generator

A CLI tool that generates unique fantasy RPG spell descriptions with arcane sigils, spell diagrams, incantations, mana costs, tags, and backstories. Perfect for Dungeon Masters, game designers, or anyone who wants procedural spell content.

**Version 3.0.0** — Now with mana costs, spell tags, synergy detection, side-by-side comparison, Markdown export, and save/load support.

## Features

- **8 schools of magic** — Abjuration, Conjuration, Divination, Enchantment, Evocation, Illusion, Necromancy, Transmutation
- **10 spell levels** — Cantrip (0) through 9th level
- **5 rarity tiers** — Common, Uncommon, Rare, Very Rare, Legendary (with weighted random selection)
- **Arcane sigils** — Procedurally generated runic symbols using elder futhark and geometric patterns
- **Spell diagrams** — Geometric spell circles with unique configurations per spell
- **Incantations** — School-themed verbal components with dramatic phrasing
- **Backstories** — Procedurally generated lore for each spell
- **🆕 Mana cost system** — Calculated from spell level, school, rarity, casting time, and duration
- **🆕 Spell tags** — Thematic categorization (e.g., "fire", "damage", "cantrip", "epic") for filtering and organization
- **🆕 Spell synergy detection** — Find pairs of spells that work well together (`--synergies`)
- **🆕 Side-by-side comparison** — Compare two spells visually (`--compare`)
- **🆕 Markdown export** — Clean Markdown output for wikis and documentation (`--markdown`)
- **🆕 Save/Load** — Persist generated spells to JSON files (`--save`/`--load`)
- **Grammar-aware descriptions** — Singular/plural nouns handled correctly
- **Correct ordinals** — "1st", "2nd", "3rd", "11th", "21st", etc.
- **Aligned box rendering** — Consistent 64-character width for all spell pages
- **Color and plaintext output** — ANSI color support with `--no-color` fallback
- **JSON export** — Structured output for integration with other tools (`--json`)
- **File output** — Write results to a file (`--output`)
- **Seed support** — Reproducible generation with `--seed`
- **Interactive mode** — Browse spells, compare, find synergies, and manage history
- **Spell list mode** — Compact table of generated spells with mana costs (`--list`)
- **84 unit tests** — Comprehensive test coverage

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

### JSON output (includes tags and mana_cost)

```bash
python3 grimoire.py --json --count 3
```

### Markdown output

```bash
python3 grimoire.py --markdown --seed 42
```

### Spell list (compact table with mana costs)

```bash
python3 grimoire.py --list 10
```

### 🆕 Compare two spells side-by-side

```bash
python3 grimoire.py --compare --seed 42
```

### 🆕 Find spell synergies

```bash
python3 grimoire.py --synergies 5
python3 grimoire.py --synergies 5 --school Evocation
```

### 🆕 Save spells to a file

```bash
python3 grimoire.py --count 3 --save my_spells.json
```

### 🆕 Load and display spells from a file

```bash
python3 grimoire.py --load my_spells.json
python3 grimoire.py --load my_spells.json --json
python3 grimoire.py --load my_spells.json --markdown
```

### Save to file (plaintext)

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

## What's New in v3.0.0

### Mana Cost System
Every spell now has a calculated **mana cost** based on:
- **Spell level** — Base cost ranges from 0 (Cantrip) to 75 (9th level)
- **School difficulty** — Conjuration (1.15×) costs more; Divination (0.85×) costs less
- **Rarity** — Legendary adds +20, Common adds +0
- **Casting time** — Quick casts (1 action, bonus action, reaction) add +3
- **Duration** — Long durations ("Until dispelled", "24 hours") add +5; Concentration adds +2

Mana costs appear in both the box rendering and JSON/Markdown output.

### Spell Tags
Each spell gets thematic **tags** based on its school, level, rarity, and damage type. Examples:
- Evocation: `evocation, fire, damage, burst`
- Necromancy: `necromancy, death, curse, cantrip`
- Legendary spells: `legendary, epic`

Tags are included in JSON export, Markdown export, and displayed in the interactive mode.

### Spell Synergy Detection
The `--synergies N` flag generates N spells and identifies pairs that work well together based on school pairings (e.g., Evocation + Abjuration = battle mage synergy). Includes a readable description of why each pair synergizes.

### Side-by-Side Comparison
The `--compare` flag generates two random spells and renders them side-by-side for easy comparison.

### Markdown Export
The `--markdown` flag outputs each spell as a clean Markdown document with headers, bullet lists, and sections — perfect for wikis, Obsidian, or documentation.

### Save/Load
Use `--save FILE` to persist generated spells to JSON, and `--load FILE` to recall them later. Loaded spells can be displayed in any format (box, JSON, Markdown).

### Interactive Mode Enhancements
The interactive browser now includes:
- Option 7: Compare two spells side-by-side
- Option 8: Find synergies in recent spells
- Option 9: View spell history
- Options s/l: Save/load spells to/from JSON files
- Tags and mana costs displayed after each spell

## Example Output

### Box Rendering (terminal)

```
  ╔════════════════════════════════════════════════════════════╗
  ║ Necromancy — 3rd Level                                     ║
  ║ [Rare]  Mana: 20                                           ║
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
  ... (spell diagram, description, tags, incantation, lore)
  ╚════════════════════════════════════════════════════════════╝
```

### Markdown Rendering

```markdown
# Twilight Grasp

**Necromancy — 3rd Level** | **[Rare]** | **Mana Cost: 20**

- **Casting Time:** 1 hour
- **Range:** 60 feet
- **Duration:** 8 hours
- **Components:** V, S, M (a copper coin and ground stardust)

## Description

Drains 2d8 hit points from the target, healing the caster by half.

## At Higher Levels

When cast using a 4th level or higher, the damage increases for each slot level above 3.

## Tags

necromancy, shadow, drain, rare
```

## Mana Cost Table

| Level | Base Cost | Example (Evocation, Common) |
|-------|-----------|------------------------------|
| 0 (Cantrip) | 0 | 0–3 (modifiers only) |
| 1st | 5 | 5–8 |
| 2nd | 10 | 10–13 |
| 3rd | 15 | 15–18 |
| 5th | 30 | 30–33 |
| 7th | 50 | 50–53 |
| 9th | 75 | 75–78 |

*Final cost = base × school_multiplier + rarity_modifier + casting_time_modifier + duration_modifier*

## Synergy Pairs

| Schools | Synergy |
|---------|---------|
| Evocation + Abjuration | Offensive spells pair with protective wards for battle mages |
| Necromancy + Evocation | Dark energy amplifies destructive force |
| Enchantment + Illusion | Mind-altering magic and deception create irresistible effects |
| Conjuration + Abjuration | Summoned allies reinforced by barriers are formidable |
| Divination + Enchantment | Knowledge of thoughts makes enchantment more effective |
| Transmutation + Evocation | Altered forms channel elemental energy efficiently |

## How It Works

### Procedural Generation

Spells are assembled from large word pools:
- **56 prefixes** (Abyssal, Arcane, Zealous, etc.)
- **16 roots per school** (Bolt, Grasp, Scry, etc.)
- **30 reagents** for material components
- **8 verbal** and **8 somatic** component descriptions
- **7 backstory templates** with 8+ fill-in categories
- **32 incantation verbs** for ritual phrases

### Rarity System

Rarity is selected with weighted probabilities and level-appropriate biases:

| Rarity | Weight | Level Range |
|--------|--------|-------------|
| Common | 40 | 0–2 |
| Uncommon | 30 | 1–3 |
| Rare | 18 | 3–5 |
| Very Rare | 9 | 5–7 |
| Legendary | 3 | 7–9 |

### Name Uniqueness

The generator tracks all names produced in a session and retries up to 50 times to avoid duplicates.

## License

MIT