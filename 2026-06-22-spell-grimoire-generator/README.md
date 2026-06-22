# 📜 Spell Grimoire Generator v2.0

A procedural spell grimoire generator for fantasy RPG campaigns. Creates beautifully formatted grimoire pages complete with arcane sigils, spell diagrams, ritual incantations, reagent lists, rarity tiers, and rich lore backstories — all generated procedurally with school-specific theming.

## Features

- **8 Schools of Magic**: Evocation, Necromancy, Enchantment, Illusion, Conjuration, Abjuration, Divination, and Transmutation — each with unique spell roots, effect templates, sigil symbols, and color themes
- **5 Rarity Tiers**: Common, Uncommon, Rare, Very Rare, and Legendary — each with level-appropriate bias and color-coded display
- **Procedural Spell Names**: Combines prefix/root pools per school for names like "Abyssal Eruption", "Whispering Chill", or "Abyssal Eruption of Ebon Fury"
- **ASCII Arcane Sigils**: Each spell gets a unique procedural sigil with school-specific symbols (⚡ for Evocation, ☠ for Necromancy, etc.) and level-based runic marks using elder futhark characters
- **Geometric Spell Diagrams**: Procedurally generated geometric patterns that vary by school and spell level — pentagrams, hexagrams, star patterns with connecting lines
- **Ritual Incantations**: Generated spell incantations with school-appropriate invocations ("By shadow and starlight!", "I command thee!")
- **Rich Lore Backstories**: Each spell gets a procedurally generated historical backstory referencing forgotten temples, legendary archmages, ancient eras, and cursed codices — with 7 unique backstory templates
- **Color-Coded Output**: Each school gets a distinct terminal color (red for Evocation, purple for Necromancy, gold for Conjuration, etc.)
- **JSON Export**: Output spells as structured JSON data for integration with other tools
- **Multiple Output Modes**: Single spell, multiple spells, full grimoire (5 spells), compact spell list, or interactive browser
- **Rarity-Aware Level Bias**: Legendary spells tend toward higher levels, Common spells tend toward lower levels
- **Unique Spell Names**: Session-tracking ensures no duplicate spell names within a run
- **Correct Ordinal Suffixes**: "At Higher Levels" text uses proper ordinals (1st, 2nd, 3rd, 11th, etc.)
- **Reproducible Seeds**: Use `--seed` for deterministic output — great for sharing specific spells
- **File Export**: Save plaintext grimoires to files with ANSI codes stripped
- **`--version` Flag**: Shows the current version number
- **Random State Isolation**: Sigil and diagram generation preserves the global random state — no side effects

## Installation

No external dependencies required — uses only Python 3 standard library:

```bash
# No install needed, just run directly:
python3 grimoire.py

# Or make it executable:
chmod +x grimoire.py
./grimoire.py
```

## Usage

### Generate a Random Spell
```bash
python3 grimoire.py
```

### Generate a Spell from a Specific School
```bash
python3 grimoire.py --school Necromancy
python3 grimoire.py -s Evocation
```

Available schools: Evocation, Necromancy, Enchantment, Illusion, Conjuration, Abjuration, Divination, Transmutation

### Generate a Specific Spell Level
```bash
python3 grimoire.py --level 9    # 9th-level spell (epic!)
python3 grimoire.py --level 0    # Cantrip
python3 grimoire.py -s Illusion -l 3  # 3rd-level Illusion spell
```

### Generate with a Specific Rarity
```bash
python3 grimoire.py --rarity Legendary     # Legendary-rarity spell
python3 grimoire.py -r Rare -l 5           # Rare 5th-level spell
```

Available rarities: Common, Uncommon, Rare, Very Rare, Legendary

### Generate Multiple Spells
```bash
python3 grimoire.py --count 3              # 3 separate spell pages
python3 grimoire.py -c 5 -s Necromancy    # 5 Necromancy spells
```

### Generate a Full Grimoire (5 Spells)
```bash
python3 grimoire.py --grimoire
python3 grimoire.py -g -s Necromancy   # All Necromancy
```

### Generate a Spell List (Compact Table)
```bash
python3 grimoire.py --list 20          # 20 random spells
python3 grimoire.py -n 10 -s Evocation # 10 Evocation spells
```

### JSON Output
```bash
python3 grimoire.py --json             # Single spell as JSON
python3 grimoire.py --json --count 5   # 5 spells as JSON array
python3 grimoire.py --json -s Divination --level 7  # Specific spell as JSON
```

### Interactive Mode
```bash
python3 grimoire.py --interactive
python3 grimoire.py -i
```

### Reproducible Output (Seed)
```bash
python3 grimoire.py --seed 42          # Same seed = same spell every time
```

### Save to File
```bash
python3 grimoire.py --grimoire -o my_grimoire.txt
python3 grimoire.py -s Divination -o divination_spell.txt
```

### Disable Colors
```bash
python3 grimoire.py --no-color
```

### Show Version
```bash
python3 grimoire.py --version
```

## Example Output

```
  ╔════════════════════════════════════════════════════════════╗
  ║ Necromancy — Cantrip Level                                 ║
  ║ [Common]                                                   ║
  ╠════════════════════════════════════════════════════════════╣
  ║ Zealous Command                                            ║
  ╠────────────────────────────────────────────────────────────╣
  ║ Casting Time: 8 hours                                     ║
  ║ Range: Self                                               ║
  ║ Duration: Instantaneous                                   ║
  ║ Components: V, S                                          ║
  ╠────────────────────────────────────────────────────────────╣
  ║                                                            ║
  ║            ○                                                ║
  ║          ··|··                                              ║
  ║        ·········                                            ║
  ║       ···◠ ☠ ◡···                                           ║
  ║        ·········                                            ║
  ║          ··|··                                              ║
  ║            ○                                                ║
  ║                                                            ║
  ╠────────────────────────────────────────────────────────────╣
  ║                                                            ║
  ║ Drains 1d12 hit points from the target, healing the        ║
  ║ caster by half.                                            ║
  ║                                                            ║
  ╠────────────────────────────────────────────────────────────╣
  ║ Verbal: the spell requires a spoken confession of a        ║
  ║ secret                                                     ║
  ║                                                            ║
  ╠────────────────────────────────────────────────────────────╣
  ║  "By dark beyond life, forsake and shine — let the         ║
  ║  world tremble!"                                           ║
  ║                                                            ║
  ╠────────────────────────────────────────────────────────────╣
  ║                                                            ║
  ║ The Council of Everspire outlawed this spell during the    ║
  ║ Third Ascendancy after Ravendawn used it to devastating    ║
  ║ effect against the orc invasion. Copies were ordered       ║
  ║ destroyed, but a single parchment survived in the          ║
  ║ archives of the Temple of Ashenmoor.                       ║
  ║                                                            ║
  ╚════════════════════════════════════════════════════════════╝
```

## How It Works

The generator uses a layered procedural system:

1. **Rarity Selection**: Weighted random selection (Common 40%, Uncommon 30%, Rare 18%, Very Rare 9%, Legendary 3%) with level-aware bias — Legendary spells tend toward higher levels, Common spells toward lower
2. **Name Generation**: Combines a thematic prefix pool with school-specific root words. Higher-level spells may get double-barreled names (e.g., "Abyssal Eruption of Ebon Fury"). Name uniqueness is tracked per session.
3. **Sigil Generation**: Uses seeded mathematical placement on a grid — concentric circles, school-specific Unicode symbols, and elder futhark runes placed at level-appropriate angles. Random state is preserved and restored to avoid side effects.
4. **Spell Diagrams**: Procedural geometric patterns with N-sided polygons (where N = level + 2), star connections at level 3+, and school-themed center symbols
5. **Incantation Generation**: Composes ritual phrases from school-appropriate subjects, verb chains, and dramatic endings
6. **Backstory Generation**: 7 template-based lore patterns with randomized temples, archmages, eras, cities, and orders
7. **Effect Templates**: School-specific effect descriptions with randomized dice, damage types, areas, conditions, and durations

## Color Themes

| School | Color |
|-------|-------|
| Evocation | Red |
| Necromancy | Purple |
| Enchantment | Pink |
| Illusion | Cyan |
| Conjuration | Yellow |
| Abjuration | Green |
| Divination | Magenta |
| Transmutation | Orange |

| Rarity | Color |
|--------|-------|
| Common | White |
| Uncommon | Green |
| Rare | Blue |
| Very Rare | Purple |
| Legendary | Gold |

## Testing

Run the test suite:

```bash
python3 test_grimoire.py
```

The test suite covers:
- Spell generation (all schools, levels, rarities)
- Ordinal suffix correctness (1st, 2nd, 3rd, 11th, 21st, etc.)
- Name uniqueness across 50 spells
- Rarity level bias
- Rendering (plaintext, color, grimoire, spell list)
- ANSI stripping
- Sigil/deterministic generation and random state preservation
- Incantation format validation
- JSON export (dict, JSON string, Unicode handling)
- CLI flags (--help, --version, --seed, --school, --json, --rarity, file output)

## What's New in v2.0

- **Rarity system**: Spells now have 5 rarity tiers (Common → Legendary) with color-coded display and level-appropriate bias
- **`--rarity` / `-r` flag**: Generate spells of a specific rarity
- **`--count` / `-c` flag**: Generate multiple individual spell pages at once
- **`--json` / `-j` flag**: Export spell data as structured JSON for integration with other tools
- **`--version` / `-v` flag**: Show version number
- **Interactive rarity browser**: Option 6 in interactive mode lets you browse spells by rarity
- **Unique spell names**: No duplicate names within a session
- **Correct ordinals**: "At Higher Levels" now uses proper English ordinals (1st, 2nd, 3rd, 11th, etc.)
- **Random state isolation**: Sigil and diagram generation no longer pollutes the global random state
- **More backstory templates**: 7 templates (up from 5) with additional template variables (material)
- **Better plaintext mode**: `--no-color` and file output now fully strip all ANSI codes including bold/italic/dim
- **Error handling**: File I/O errors are caught and reported cleanly
- **Comprehensive test suite**: 38 tests covering all major features

## License

MIT