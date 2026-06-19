# 🦕 Procedural Dinosaur Generator

**Version 2.0.0**

Generate random dinosaurs with scientifically-informed traits, ASCII art silhouettes, and collectible trading cards! Each dinosaur gets a unique binomial name following taxonomic conventions, stats, abilities, and a formatted card display.

## Features

### Core Generation
- **Procedural Name Generation** — Binomial names built from Greek/Latin taxonomic roots (e.g., *Tyrannonax ignivomus*, *Dracomimus gracilis*)
- **8 Body Types** — Theropod, Sauropod, Ceratopsian, Ankylosaur, Stegosaur, Ornithopod, Pterosaur, Therizinosaur
- **Stat System** — Attack, Defense, Speed, and Intelligence with body-type-appropriate ranges
- **Rarity Tiers** — Common (`*---`), Uncommon (`**--`), Rare (`***-`), Legendary (`****`)
- **ASCII Art** — Unique silhouette for each body type (theropods get 2 variants!)
- **Personality Traits** — Each dinosaur has a temperament (territorial, curious, aggressive, etc.)

### Display & Cards
- **Trading Card Display** — Formatted card with all stats, appearance, personality, and special abilities
- **Side-by-Side Comparison** — Compare any two dinosaurs stat-by-stat with advantage indicators
- **DinoDex Collection** — Track your discoveries, view summaries and a Wall of Fame

### Gameplay
- **Battle System** — Pit two dinosaurs against each other with weighted stat calculation (ATK×0.35 + DEF×0.25 + SPD×0.25 + INT×0.15) with ±15% randomness for upsets
- **Tournament Mode** — Bracket-style elimination tournament for your collection; supports any number of dinosaurs (odd counts get byes)

### Data & Interop
- **JSON Export** — Export any dinosaur as structured JSON for programmatic use (`--json` flag or `j` command in interactive mode)
- **Seeded Generation** — Reproducible dinosaurs with `--seed`
- **Interactive Mode** — Browse, generate, battle, compare, and collect in a REPL

### CLI
- `--version` and `--help` flags
- `--generate` for non-interactive generation (supports count)
- `--battle` for one-off battles
- `--compare` for side-by-side comparison
- `--tournament` for bracket-style elimination
- `--json` for machine-readable output
- `--type` for specific body type generation
- `--seed` for reproducible generation
- `--no-color` for environments without ANSI support

## Installation

No dependencies required — uses only the Python standard library. Requires Python 3.7+.

```bash
# Just download and run
python3 dinosaur_generator.py

# Or make it executable
chmod +x dinosaur_generator.py
./dinosaur_generator.py --help
```

## Usage

### Interactive Mode (default)

```bash
python3 dinosaur_generator.py
```

Commands inside interactive mode:
- `g` — Generate a random dinosaur
- `b` — Battle two dinosaurs from your collection
- `c` — Compare two dinosaurs side-by-side
- `t` — Tournament (all collected dinosaurs compete)
- `l` — List your collection summary
- `w` — Wall of Fame (top stats)
- `s` — Generate with a specific seed number
- `j` — Export last dinosaur as JSON
- `q` — Quit

### Generate Dinosaurs

```bash
# Generate one dinosaur
python3 dinosaur_generator.py --generate

# Generate 5 dinosaurs
python3 dinosaur_generator.py --generate 5

# Generate with a specific seed (reproducible)
python3 dinosaur_generator.py --seed 42 --generate

# Generate a specific body type
python3 dinosaur_generator.py --type theropod --generate

# Generate as JSON
python3 dinosaur_generator.py --generate --json --seed 42

# Disable ANSI colors
python3 dinosaur_generator.py --no-color --generate
```

### Battle Mode

```bash
# Battle two random dinosaurs
python3 dinosaur_generator.py --battle

# Seeded battle for reproducibility
python3 dinosaur_generator.py --seed 42 --battle
```

### Compare Mode

```bash
# Compare two random dinosaurs side-by-side
python3 dinosaur_generator.py --compare

# Seeded comparison
python3 dinosaur_generator.py --seed 42 --compare
```

### Tournament Mode

```bash
# 8-dinosaur tournament (default)
python3 dinosaur_generator.py --tournament

# 16-dinosaur tournament
python3 dinosaur_generator.py --tournament 16

# Tournament with JSON output for the champion
python3 dinosaur_generator.py --tournament 4 --json --seed 42
```

### Available Body Types

`theropod`, `sauropod`, `ceratopsian`, `ankylosaur`, `stegosaur`, `ornithopod`, `pterosaur`, `therizinosaur`

## Example Output

```
+========================================================+
| Tyrannonax ignivomus                    **** LEGENDARY |
+--------------------------------------------------------+
| THEROPOD       | [MEAT] carnivore  | bipedal           |
| Late Jurassic            | LAVA: volcanic              |
+--------------------------------------------------------+
|  ATK: [#################.]  94       |
|  DEF: [##########........]  56       |
|  SPD: [#################.]  93       |
|  INT: [############......]  69       |
+--------------------------------------------------------+
|  L:2.6m  H:1.6m  W:30kg                                |
+--------------------------------------------------------+
|  Skin: dusty tan with white underbelly                 |
|  Feathers: display feathers on arms and tail            |
|  Temper: fearless                                       |
+--------------------------------------------------------+
|   >> Bone-crushing bite force                           |
|  Egg: oblong, 25cm, in earthen mound                   |
+========================================================+
```

### JSON Output

```bash
python3 dinosaur_generator.py --generate --json --seed 42
```

Outputs structured JSON with all dinosaur attributes including computed `full_name` and `stat_total`.

## Running Tests

```bash
python3 -m pytest test_dinosaur_generator.py -v
```

61 tests covering all core functionality including:
- Name generation and habitat influence
- Dinosaur generation (default, seeded, typed)
- Stat system ranges and rarity classification
- Size and weight bounds validation
- Card rendering (with and without color)
- Battle system output
- Side-by-side comparison
- Tournament system (including odd counts and byes)
- DinoDex collection tracker
- JSON export and round-trip validation
- CLI argument parsing and version flag
- Edge cases and robustness

## How It Works

1. **Name Generation** — Combines Greek/Latin genus prefixes (Aero-, Brachio-, etc.) with taxonomic suffixes (-saurus, -raptor, -ceratops, etc.) and Latin descriptive epithets (ferox, magnus, gracilis, etc.)

2. **Stat Allocation** — Each body type has realistic stat ranges (e.g., Ankylosaurs get high DEF but low SPD; Theropods get high ATK and SPD but variable DEF)

3. **Size Calculation** — Uses log-normal distribution for realistic size variation within each body type's range

4. **Weight Scaling** — Applies cubic scaling proportional to length with noise for natural variation

5. **Rarity** — Determined by total stat points: ≥300 = Legendary, ≥260 = Rare, ≥200 = Uncommon, else Common

6. **Battle** — Weighted score (ATK×0.35 + DEF×0.25 + SPD×0.25 + INT×0.15) with ±15% randomness for upsets

7. **Tournament** — Single-elimination bracket; odd numbers get byes; random tie-breaking for draws

## What's New in v2.0.0

- **Personality traits** — Each dinosaur now has a temperament adjective displayed on the card
- **Side-by-side comparison** — `--compare` CLI flag and `c` interactive command
- **Tournament mode** — `--tournament` CLI flag and `t` interactive command
- **JSON export** — `--json` CLI flag and `j` interactive command; `Dinosaur.to_json()` and `Dinosaur.to_dict()` methods
- **`--version` flag** — Now properly reports version (2.0.0)
- **Fixed `--type` generation** — Previously used a brute-force loop hoping to match; now directly generates the specified type
- **Fixed `--type` validation** — Invalid body types now raise `ValueError` with helpful message
- **Fixed ASCII art SyntaxWarning** — All art strings now use raw strings to prevent invalid escape sequence warnings
- **Added docstrings** — Comprehensive docstrings on all public functions and classes
- **Added 61 tests** — Full test coverage for generation, rendering, battle, comparison, tournament, JSON, and CLI

## License

MIT