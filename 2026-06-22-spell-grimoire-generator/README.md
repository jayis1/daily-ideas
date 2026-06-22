# 📜 Spell Grimoire Generator

A procedural spell grimoire generator for fantasy RPG campaigns. Creates beautifully formatted grimoire pages complete with arcane sigils, spell diagrams, ritual incantations, reagent lists, and rich lore backstories — all generated procedurally with school-specific theming.

## Features

- **8 Schools of Magic**: Evocation, Necromancy, Enchantment, Illusion, Conjuration, Abjuration, Divination, and Transmutation — each with unique spell roots, effect templates, sigil symbols, and color themes
- **Procedural Spell Names**: Combines prefix/root pools per school for names like "Abyssal Eruption", "Whispering Chill", or "Ebon Grave of Primal Blight"
- **ASCII Arcane Sigils**: Each spell gets a unique procedural sigil with school-specific symbols (⚡ for Evocation, ☠ for Necromancy, etc.) and level-based runic marks using elder futhark characters
- **Geometric Spell Diagrams**: Procedurally generated geometric patterns that vary by school and spell level — pentagrams, hexagrams, star patterns with connecting lines
- **Ritual Incantations**: Generated spell incantations with school-appropriate invocations ("By shadow and starlight!", "I command thee!")
- **Rich Lore Backstories**: Each spell gets a procedurally generated historical backstory referencing forgotten temples, legendary archmages, ancient eras, and cursed codices
- **Color-Coded Output**: Each school gets a distinct terminal color (red for Evocation, purple for Necromancy, gold for Conjuration, etc.)
- **Multiple Output Modes**: Single spell, full grimoire (5 spells), compact spell list, or interactive browser
- **Reproducible Seeds**: Use `--seed` for deterministic output — great for sharing specific spells
- **File Export**: Save plaintext grimoires to files with ANSI codes stripped

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

### Generate a Full Grimoire (5 Spells)
```bash
python3 grimoire.py --grimoire
python3 grimoire.py -g -s Necromancy   # All Necromancy
```

### Generate a Spell List (Compact Table)
```bash
python3 grimoire.py --list 20          # 20 random spells
python3 grimoire.py -n 10 -s Evocation  # 10 Evocation spells
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

## Example Output

```
  ╔════════════════════════════════════════════════════════════╗
  ║ Necromancy — Cantrip Level                                 ║
  ╠════════════════════════════════════════════════════════════╣
  ║ Echoing Howl                                               ║
  ╠────────────────────────────────────────────────────────────╣
  ║ Casting Time: 1 reaction                                  ║
  ║ Range: Touch                                              ║
  ║ Duration: Concentration, up to 1 minute                   ║
  ║ Components: V, M                                          ║
  ║   (a drop of blood)                                       ║
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
  ║  "By veil of death, bend, forsake and shine — let the     ║
  ║  world tremble!"                                           ║
  ║                                                            ║
  ╠────────────────────────────────────────────────────────────╣
  ║                                                            ║
  ║ This spell was first inscribed on the walls of the         ║
  ║ Sunken Temple of Gloomreach, discovered by the archmage    ║
  ║ Nimue Frostheart during the Age of Wonders. It is said     ║
  ║ that casting it under a full moon amplifies its power      ║
  ║ twofold.                                                   ║
  ║                                                            ║
  ╚════════════════════════════════════════════════════════════╝
```

## How It Works

The generator uses a layered procedural system:

1. **Name Generation**: Combines a thematic prefix pool with school-specific root words. Higher-level spells may get double-barreled names (e.g., "Abyssal Eruption of Ebon Fury")
2. **Sigil Generation**: Uses seeded mathematical placement on a grid — concentric circles, school-specific Unicode symbols, and elder futhark runes placed at level-appropriate angles
3. **Spell Diagrams**: Procedural geometric patterns with N-sided polygons (where N = level + 2), star connections at level 3+, and school-themed center symbols
4. **Incantation Generation**: Composes ritual phrases from school-appropriate subjects, verb chains, and dramatic endings
5. **Backstory Generation**: Template-based lore with randomized temples, archmages, eras, cities, and orders
6. **Effect Templates**: School-specific effect descriptions with randomized dice, damage types, areas, conditions, and durations

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

## License

MIT