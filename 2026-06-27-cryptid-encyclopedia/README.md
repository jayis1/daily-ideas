# 🦑 Cryptid Encyclopedia

A procedurally-generated bestiary of creatures that may or may not exist. Each cryptid is deterministically generated from its name — the same name always produces the same creature, complete with ASCII art, lore, habitat, weaknesses, and sighting reports.

## Features

- **Deterministic generation** — Every cryptid name produces a unique, consistent creature. "Mothman" will always have the same stats, art, and sightings.
- **6 ASCII art templates** — Bipedal, quadrupedal, serpentine, insectoid, amorphous, and winged creature templates with randomized features (eyes, mouths, wings, tails).
- **Rich lore** — Each cryptid comes with body type, skin texture, color, head shape, special ability, habitat, weakness, origin story, threat level, diet, activity pattern, and 2–4 sighting reports.
- **Interactive browser** — Explore the encyclopedia with an interactive prompt: look up cryptids by name, discover random ones, search by keyword, or list known entries.
- **CLI mode** — Full command-line interface with flags for random generation, listing, bulk generation, and file export.
- **Infinite variety** — Procedural name generation combines adjectives, nouns, creatures, places, and more to produce thousands of unique cryptid names.

## Installation

No dependencies required — this is pure Python 3. Just download and run:

```bash
# Clone or download
git clone <repo-url>
cd cryptid-encyclopedia

# Make executable (optional)
chmod +x cryptid_encyclopedia.py
```

Requires Python 3.6+ (uses f-strings and `random` module only).

## Usage

### Look up a specific cryptid

```bash
python3 cryptid_encyclopedia.py "The Ashen Wendigo"
python3 cryptid_encyclopedia.py Mothman
python3 cryptid_encyclopedia.py "The Hollow Stalker of Blackwood"
```

### Generate random cryptids

```bash
# Single random cryptid
python3 cryptid_encyclopedia.py --random

# Generate 5 random cryptids
python3 cryptid_encyclopedia.py --random -n 5
```

### List known cryptids

```bash
python3 cryptid_encyclopedia.py --list
```

### Export to file

```bash
python3 cryptid_encyclopedia.py "Mothman" --export cryptids.txt
```

### Interactive mode

```bash
python3 cryptid_encyclopedia.py --interactive
```

In interactive mode, you can:
- Type any name to look up or create a cryptid
- Type `random` to discover a random cryptid
- Type `list` to see known cryptid names
- Type `search` followed by a keyword to search
- Type `help` for the command reference
- Type `quit` to exit

### Example Output

```
╔════════════════════════════════════════════════════════════════╗
║                   GRISTLE BARGHEST OF THE MERES                ║
╔════════════════════════════════════════════════════════════════╗
║                                _______                          ║
║                              /       \                          ║
║                             /  ✺  ✺  \                          ║
║                            |  ∧      |                          ║
║                           |   \____/   |                        ║
║                            \__________/                         ║
║                               |  ∿  |                           ║
║                              /|  ∿  |\                          ║
║                            / |      | \                         ║
║ ...
╟────────────────────────────────────────────────────────────────╢
║  THREAT LEVEL: ★★★★★★★                                       ║
║  Existential — classified threat by 3+ governments             ║
╟────────────────────────────────────────────────────────────────╢
║  Body Type: vermiform                                          ║
║  Height: 12m                                                   ║
║  Weight: 50kg                                                  ║
║  Diet: hematophagic                                            ║
╟────────────────────────────────────────────────────────────────╢
║ A ozone silver, smoldering vermiform creature with a amorphous ║
║ and constantly shifting head. It hibernates for decades then   ║
║ emerges ravenous. Origin: a creature that has existed since    ║
║ before the Permian extinction, merely sleeping.                 ║
╟────────────────────────────────────────────────────────────────╢
║  WEAKNESS: cannot enter any structure with a threshold offering║
╟────────────────────────────────────────────────────────────────╢
║  SIGHTING REPORTS                                              ║
║  1. An elderly resident finally reported it in 1990.            ║
║  2. A mining crew 2km underground radioed about it in 1984.    ║
╚════════════════════════════════════════════════════════════════╝
```

## How It Works

1. **Seeding** — The cryptid name is hashed with SHA-256 and converted to an integer seed for Python's `random.Random`. This ensures deterministic output.
2. **Template selection** — One of 6 ASCII art templates is selected, with feature characters (eyes, mouths, wings, tails) randomly filled in from themed character pools.
3. **Procedural lore** — Body type, skin texture, color, head shape, ability, habitat, weakness, origin, threat level, stats, and sighting reports are all picked from curated pools using the seeded RNG.
4. **Name generation** — When generating random names, the format strings combine adjectives, nouns, creature types, and place names for thousands of unique combinations.

## License

MIT