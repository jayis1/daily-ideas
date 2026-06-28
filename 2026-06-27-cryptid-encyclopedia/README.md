# 🦑 Cryptid Encyclopedia

A procedurally-generated bestiary of creatures that may or may not exist. Each cryptid is deterministically generated from its name — the same name always produces the same creature, complete with ASCII art, lore, habitat, weaknesses, and sighting reports. Look up classics like Mothman or invent your own and see what the algorithm conjures.

## Features

- **Deterministic generation** — Every name produces a unique, consistent creature. "Mothman" always has the same stats, art, and sightings.
- **6 ASCII art templates** — Bipedal, quadrupedal, serpentine, insectoid, amorphous, and winged templates with randomized feature characters (eyes, mouths, wings, tails). Art template selection is influenced by body type.
- **Rich lore** — Each cryptid has body type, skin texture, color, head shape, special ability, habitat, weakness, origin story, threat level (1–7 stars), diet, activity pattern, and 2–4 sighting reports.
- **Interactive browser** — Explore with a prompt: look up, random, search, compare, related, history, and compact mode.
- **Side-by-side comparison** — `--compare` shows two cryptids in a stat-by-stat table.
- **JSON output** — `--json` for scripting, pipelines, or further processing. Multiple results (`-n > 1`) output a JSON array.
- **Compact mode** — `--compact` for a one-paragraph summary instead of the full boxed display.
- **Reproducible randomness** — `--seed 42` makes random generation deterministic for sharing.
- **Related cryptids** — `related` command in interactive mode finds cryptids that share traits with the one you just viewed.
- **History tracking** — Interactive mode remembers your recently viewed cryptids.
- **Export to file** — `--export file.txt` appends formatted entries to a file (creates parent directories automatically).
- **Input validation** — Empty names and negative counts are rejected with clear error messages. Whitespace and tabs in names are normalized.
- **Proper articles** — Descriptions and sighting reports use "An"/"an" before vowel-starting words ("An ozone silver..." not "A ozone silver...").
- **Aligned box display** — All lines in the boxed display are consistently 70 characters wide.
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
# Single cryptid as JSON object
python3 cryptid_encyclopedia.py Mothman --json

# Single random cryptid as JSON object
python3 cryptid_encyclopedia.py --random --json

# Multiple random cryptids as JSON array
python3 cryptid_encyclopedia.py --random -n 3 --json --seed 42

# Compare as JSON array
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
# Export a cryptid entry (appends to the file)
python3 cryptid_encyclopedia.py Mothman --export cryptids.txt

# Export with automatic directory creation
python3 cryptid_encyclopedia.py Mothman --export output/cryptids.txt
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
╔────────────────────────────────────────────────────────────────────╗
║                              MOTHMAN                               ║
╠════════════════════════════════════════════════════════════════════╣
║                                   ⊙  ⊙  ⊙                          ║
║                               /   \  ▽ /   \                       ║
║                            /     \____/     \                      ║
║                           /   §         §   \                      ║
╟────────────────────────────────────────────────────────────────────╢
║  THREAT LEVEL: ★★★★☆☆☆                                             ║
║  Dangerous — known to have injured humans                          ║
╟────────────────────────────────────────────────────────────────────╢
║  Body Type: vermiform                                              ║
║  Height: 0.8m                                                      ║
║  Weight: 2kg                                                       ║
║  Diet: carnivorous                                                 ║
║  Activity: nocturnal                                               ║
╟────────────────────────────────────────────────────────────────────╢
║ An ozone silver, furry bipedal creature with an amorphous and      ║
║ constantly shifting head. It can become invisible in fog.          ║
║ Origin: a dimensional refugee that slipped through thin reality.   ║
╟────────────────────────────────────────────────────────────────────╢
║  HABITAT: abandoned nuclear testing sites in Kazakhstan             ║
╟────────────────────────────────────────────────────────────────────╢
║  WEAKNESS: loses power during the new moon                          ║
╟────────────────────────────────────────────────────────────────────╢
║  SIGHTING REPORTS                                                  ║
║────────────────────────────────────────────────────────────────────║
║   1. An elderly resident finally reported an Ooze Moth in 1990.   ║
║   It circled their campsite for six hours.                         ║
╚════════════════════════════════════════════════════════════════════╝
```

## How It Works

1. **Seeding** — The cryptid name is hashed with SHA-256 and converted to an integer seed for Python's `random.Random`. This ensures deterministic output — the same name always produces the same creature. Case and whitespace are normalized, so "Mothman" and "mothman" produce identical results.
2. **Template selection** — One of 6 ASCII art templates is selected, influenced by the creature's body type (70% chance of matching, 30% random for variety). Feature characters (eyes, mouths, wings, tails) are randomly filled from themed character pools.
3. **Procedural lore** — Body type, skin texture, color, head shape, ability, habitat, weakness, origin, threat level, stats, and sighting reports are all picked from curated pools using the seeded RNG.
4. **Name generation** — When generating random names, format strings combine adjectives, nouns, creature types, and place names for thousands of unique combinations.
5. **Related cryptids** — The `related` command compares body type, skin, color, diet, and activity to find cryptids that share the most traits with your last viewed entry.

## Testing

```bash
python3 test_cryptid_encyclopedia.py
```

Runs 40 tests covering determinism, generation, display alignment, article grammar, JSON output (single and array), CLI flags, empty/invalid input handling, export functionality, and more.

## Changelog

### v1.2.0 — Bug fixes and improvements
- **Fixed box alignment** — Threat level and description lines were too short (27 and 68 chars instead of 70). All lines now consistently use `BOX_WIDTH` padding.
- **Fixed title separator** — Changed second top border from `╔╗` to `╠═╣` (double-line separator) for proper box drawing.
- **Fixed article grammar** — Descriptions now use "An" before vowel-starting colors ("An ozone silver" instead of "A ozone silver") and "an" before vowel-starting head shapes ("with an amorphous head" instead of "with a amorphous head"). Sightings also correctly use "an" for vowel-starting names.
- **Fixed crash on empty name** — Passing an empty string as a cryptid name caused an `IndexError`. Empty and whitespace-only names are now rejected with a clear error message.
- **Fixed crash on export to nonexistent directory** — `--export` now creates parent directories automatically instead of crashing with `FileNotFoundError`.
- **Fixed JSON output for multiple cryptids** — `--random -n N --json` previously output N separate JSON objects (invalid JSON). Now outputs a proper JSON array when N > 1, and a single object when N = 1.
- **Fixed negative `--number` handling** — `--random -n -1` previously produced empty output silently. Now produces a clear error message.
- **Fixed name whitespace normalization** — Tabs, newlines, and multiple spaces in names are now collapsed to single spaces, preventing display misalignment.
- **Added `hr_double()` function** — New display helper for double-line separators in boxed output.

## License

MIT