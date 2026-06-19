# 🦕 Procedural Dinosaur Generator

Generate random dinosaurs with scientifically-informed traits, ASCII art silhouettes, and collectible trading cards! Each dinosaur gets a unique binomial name following taxonomic conventions, stats, abilities, and a formatted card display.

## Features

- **Procedural Name Generation** — Binomial names built from Greek/Latin taxonomic roots (e.g., *Tyrannonax ignivomus*, *Dracomimus gracilis*)
- **8 Body Types** — Theropod, Sauropod, Ceratopsian, Ankylosaur, Stegosaur, Ornithopod, Pterosaur, Therizinosaur
- **Stat System** — Attack, Defense, Speed, and Intelligence with body-type-appropriate ranges
- **Rarity Tiers** — Common (*), Uncommon (**), Rare (***), Legendary (****)
- **ASCII Art** — Unique silhouette for each body type
- **Trading Card Display** — Formatted card with all stats, appearance, and special abilities
- **Battle System** — Pit two dinosaurs against each other with weighted stat calculation
- **DinoDex Collection** — Track your discoveries, view summaries and a Wall of Fame
- **Seeded Generation** — Reproducible dinosaurs with `--seed`
- **Interactive Mode** — Browse, generate, battle, and collect in a REPL

## Installation

No dependencies required — uses only the Python standard library.

```bash
# Just download and run
python3 dinosaur_generator.py
```

## Usage

### Interactive Mode (default)

```bash
python3 dinosaur_generator.py
```

Commands inside interactive mode:
- `g` — Generate a random dinosaur
- `b` — Battle two dinosaurs from your collection
- `l` — List your collection summary
- `w` — Wall of Fame (top stats)
- `s` — Generate with a specific seed number
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

# Disable ANSI colors
python3 dinosaur_generator.py --no-color --generate
```

### Battle Mode

```bash
# Battle two random dinosaurs
python3 dinosaur_generator.py --battle
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
|  Feathers: display feathers on arms and tail           |
+--------------------------------------------------------+
|   >> Bone-crushing bite force                           |
|  Egg: oblong, 25cm, in earthen mound                   |
+========================================================+
```

## How It Works

1. **Name Generation** — Combines Greek/Latin genus prefixes (Aero-, Brachio-, etc.) with taxonomic suffixes (-saurus, -raptor, -ceratops, etc.) and Latin descriptive epithets (ferox, magnus, gracilis, etc.)

2. **Stat Allocation** — Each body type has realistic stat ranges (e.g., Ankylosaurs get high DEF but low SPD; Theropods get high ATK and SPD but variable DEF)

3. **Size Calculation** — Uses log-normal distribution for realistic size variation within each body type's range

4. **Weight Scaling** — Applies cubic scaling proportional to length with noise for natural variation

5. **Rarity** — Determined by total stat points: ≥300 = Legendary, ≥260 = Rare, ≥200 = Uncommon, else Common

6. **Battle** — Weighted score (ATK×0.35 + DEF×0.25 + SPD×0.25 + INT×0.15) with ±15% randomness for upsets

## What It Does

This is a fun procedural generation tool that creates unique dinosaurs each time you run it. It's inspired by collectible card games and paleontology — every dinosaur has scientifically plausible traits based on its body type, a unique taxonomic name, detailed appearance description, and gameplay-style stats. The battle system and DinoDex collection tracker add replayability.