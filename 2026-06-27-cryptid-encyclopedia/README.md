# 🦑 Cryptid Encyclopedia

A procedurally-generated bestiary of creatures that may or may not exist. Each cryptid is deterministically generated from its name — the same name always produces the same creature, complete with ASCII art, lore, habitat, weaknesses, and sighting reports. Look up classics like Mothman or invent your own and see what the algorithm conjures.

## Features

- **Deterministic generation** — Every name produces a unique, consistent creature. "Mothman" always has the same stats, art, and sightings.
- **6 ASCII art templates** — Bipedal, quadrupedal, serpentine, insectoid, amorphous, and winged templates with randomized feature characters (eyes, mouths, wings, tails). Art template selection is influenced by body type — a serpentine creature is more likely to get the serpentine template.
- **Rich lore** — Each cryptid has body type, skin texture, color, head shape, special ability, habitat, weakness, origin story, threat level (1–7 stars), diet, activity pattern, and 2–4 sighting reports.
- **Interactive browser** — Explore with a prompt: look up, random, search, compare, related, history, and compact mode.
- **Side-by-side comparison** — `--compare` shows two cryptids in a stat-by-stat table.
- **JSON output** — `--json` for scripting, pipelines, or further processing.
- **Compact mode** — `--compact` for a one-paragraph summary instead of the full boxed display.
- **Reproducible randomness** — `--seed 42` makes random generation deterministic for sharing.
- **Related cryptids** — `related` command in interactive mode finds cryptids that share traits with the one you just viewed.
- **History tracking** — Interactive mode remembers your recently viewed cryptids.
- **CLI with `--version`** — Full command-line interface with help, version, export, and all the flags above.
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

# Reproducible random generation (same seed = same results)
python3 cryptid_encyclopedia.py --random --seed 42
```

### Compare two cryptids side-by-side

```bash
python3 cryptid_encyclopedia.py --compare "The Ashen Wendigo" "The Hollow Stalker of Blackwood"
```

### JSON output (for scripting)

```bash
python3 cryptid_encyclopedia.py Mothman --json
python3 cryptid_encyclopedia.py --random --json
python3 cryptid_encyclopedia.py --compare "A" "B" --json
```

### Compact display

```bash
python3 cryptid_encyclopedia.py Mothman --compact
python3 cryptid_encyclopedia.py --random --compact
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
- Type `related` to find cryptids that share traits with the last one you viewed
- Type `compare` to compare the last viewed cryptid with another side-by-side
- Type `compact` to toggle compact display mode
- Type `history` to see recently viewed cryptids
- Type `help` for the command reference
- Type `quit` to exit

### Version

```bash
python3 cryptid_encyclopedia.py --version
```

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

1. **Seeding** — The cryptid name is hashed with SHA-256 and converted to an integer seed for Python's `random.Random`. This ensures deterministic output — the same name always produces the same creature. Case and leading/trailing whitespace are normalized, so "Mothman" and "mothman" produce identical results.
2. **Template selection** — One of 6 ASCII art templates is selected, influenced by the creature's body type (70% chance of matching, 30% random for variety). Feature characters (eyes, mouths, wings, tails) are randomly filled from themed character pools.
3. **Procedural lore** — Body type, skin texture, color, head shape, ability, habitat, weakness, origin, threat level, stats, and sighting reports are all picked from curated pools using the seeded RNG.
4. **Name generation** — When generating random names, format strings combine adjectives, nouns, creature types, and place names for thousands of unique combinations.
5. **Related cryptids** — The `related` command compares body type, skin, color, diet, and activity to find cryptids that share the most traits with your last viewed entry.

## Testing

```bash
python3 test_cryptid_encyclopedia.py
```

Runs 26 tests covering determinism, generation, display, JSON output, CLI flags, and more.

## License

MIT