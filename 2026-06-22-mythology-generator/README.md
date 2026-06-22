# Procedural Mythology Generator

Generate complete, original fictional mythologies — pantheons of gods with domains, relationships, creation myths, sacred narratives, cosmologies, and taboos. Every run produces a unique, internally consistent mythology that reads like it came from a lost civilization.

## Features

- **Pantheon Generation** — Create 3–12 gods, each with a unique name, title, primary and secondary domains, sacred symbol, physical description, personality, worship practices, and taboos
- **Creation Myths** — Choose from 6 distinct myth templates: cosmic eggs, primordial collisions, dreaming gods, mortal ascensions, and more
- **Cosmological Structures** — World-trees, cosmic wheels, great songs, layered realms — each pantheon gets a unique vision of how the cosmos is shaped
- **Divine Relationships** — Gods are connected as siblings, parents/children, spouses, rivals, allies, creators, deceivers, guardians — each with a short narrative
- **Sacred Narratives** — Procedurally generated myths: thefts, wars, bindings, descents, betrayals — each weaving the pantheon's gods into dramatic stories
- **The Great Taboo** — Every mythology has a supreme prohibition that mortals must never transgress
- **Reproducible Output** — Set a seed to regenerate the same mythology
- **Multiple Formats** — Output as rich Markdown or structured JSON

## Installation

No dependencies required — uses only Python standard library modules:

```bash
# No install needed, just download and run
python3 mythology_generator.py
```

## Usage

### Basic — generate a mythology with 7 gods

```bash
python3 mythology_generator.py
```

### Specify number of gods (3–12)

```bash
python3 mythology_generator.py --gods 5
python3 mythology_generator.py --gods 12
```

### Set a seed for reproducible results

```bash
python3 mythology_generator.py --seed 42 --gods 7
```

### Output as JSON

```bash
python3 mythology_generator.py --format json
```

### Save to file

```bash
python3 mythology_generator.py --output my_pantheon.md
python3 mythology_generator.py --format json --output my_pantheon.json
```

### Full options

```
usage: mythology_generator.py [-h] [--gods GODS] [--seed SEED]
                               [--format {markdown,json}] [--output OUTPUT]

Procedural Mythology Generator — create complete fictional pantheons

options:
  -h, --help            show this help message and exit
  --gods GODS, -g GODS  Number of gods to generate (3-12, default: 7)
  --seed SEED, -s SEED  Random seed for reproducibility
  --format {markdown,json}, -f {markdown,json}
                        Output format (default: markdown)
  --output OUTPUT, -o OUTPUT
                        Output file path (default: stdout)
```

## Example Output

```
# The Silent Pantheon of Helion

---

## The Creation

A great cosmic egg floated in the Deep Quiet for an age beyond counting.
When it could contain itself no longer, it split — its shell became the
sky and earth, its yolk became the sun, and its white became the moon.
Helion the Gentle emerged from the embryo, already ancient, already wise.
The other gods were the egg's memories, given form.

## The Shape of the Cosmos

The world is a wheel turned by Naran the Still. Each spoke is an age,
and mortals cling to the rim, believing they move forward. The gods sit
at the hub, watching the same stories repeat. Only Naran the Still
knows what lies beyond the wheel.

## The Gods

### Helion the Gentle

**Domain:** Fire
**Also:** Thresholds
**Symbol:** A brazier

When Helion walks the world, flowers bloom. They are known by a brazier,
and those who encounter them are forever changed.

Patient and watchful, Helion demands absolute devotion. Helion is slow
to anger but terrible in wrath.

*Worship:* singing Helion's true name only in whispers.

*Taboo:* It is forbidden to speak Helion's name within sight of the sea.

...
```

## How It Works

1. **Name generation** — Combines fantasy prefixes (Aeth-, Bal-, Cor-, etc.) with suffixes (-ion, -ath, -el, etc.) to create unique god names
2. **Domain assignment** — Each god claims a primary domain and 1–3 secondary domains; domains are never repeated across the pantheon
3. **Creation myth** — Randomly selects from 6 mythic templates (cosmic egg, dream, collision, etc.) and fills in the pantheon's first god
4. **Cosmology** — Picks from 5 cosmological models (great tree, wheel, song, layered realms, etc.) and assigns gods to cosmic roles
5. **Relationships** — Generates (n-1) to (2n) relationships between gods, each with a type (sibling, rival, spouse, etc.) and a short narrative
6. **Sacred narratives** — Generates 2–4 myths (thefts, wars, bindings, descents, betrayals) using template structures populated with the pantheon's gods
7. **Great taboo** — Creates a universal prohibition tied to one of the gods

## Use Cases

- **Worldbuilding** for tabletop RPGs, novels, and games
- **Creative prompts** for writing and art
- **Procedural content** for games that need lore generation
- **Teaching mythology** — Compare generated myths to real-world mythological structures
- **Fun** — Every mythology is a surprise

## License

MIT