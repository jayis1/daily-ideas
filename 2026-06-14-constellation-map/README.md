# ✦ Constellation Map — Procedural Star Atlas Generator

A command-line tool that generates rich, navigable ASCII star maps with procedurally created constellations, mythical names, deep sky objects, nebulae, and lore. Every map is unique — seeded by your choice or left to chance.

![CLI output example](https://img.shields.io/badge/output-ASCII%20Art-blue)

## Features

- **Procedural constellation generation** — 6 distinct shapes (chain, triangle, cross, arc, cluster, spiral) with randomly generated mythological names and titles
- **Greek letter star designations** — Brightest stars in each constellation get proper α, β, γ… labels
- **Nebulae** — Colored ASCII nebulae (░▒▓) that cloud regions of the sky
- **Deep sky objects** — Galaxies, pulsars, quasars, black holes, star clusters, and more
- **Rich lore engine** — Template-based lore generator fills in mythological stories for each constellation
- **Reproducible maps** — Use `--seed` to generate the exact same map every time
- **JSON export** — Export the full star catalog as structured JSON data
- **Configurable rendering** — Toggle colors, constellation lines, labels, and more
- **ANSI color support** — Beautiful terminal rendering with color-coded stars, nebulae, and objects

## Installation

No dependencies required — uses only the Python standard library.

```bash
# Clone or download, then run directly:
python3 constellation_map.py
```

## How to Run

```bash
# Generate a random star map
python3 constellation_map.py

# Reproducible map with a specific seed
python3 constellation_map.py --seed 42

# Larger map with more constellations
python3 constellation_map.py --width 120 --height 50 --constellations 20

# Disable ANSI colors (for pipes, files, or simple terminals)
python3 constellation_map.py --no-color

# Hide constellation connection lines
python3 constellation_map.py --no-lines

# Hide constellation name labels on the map
python3 constellation_map.py --no-labels

# Compact output — just the visual map, no catalog
python3 constellation_map.py --compact

# Show only the constellation catalog (no visual map)
python3 constellation_map.py --catalog-only

# Export star data as JSON
python3 constellation_map.py --export atlas.json
```

## Usage Examples

### Basic random map
```
$ python3 constellation_map.py --seed 777 --width 80 --height 30 --no-color

✦ Celestial Atlas — Procedural Constellation Map ✦
                                            Seed: 000777

┌────────────────────────────────────────────────────────────────────────────────┐
│   ∘                                             ·                              │
│             ·            ∘  ∘  ⋆  ·     ·        ∘          ·                 ⋆│
│                         ∘           ∘      ·∘· ∘     ∘   · ∘     ∘  ∘    ∘     │
│           ∘  ✧ ✶    ·   ✶          ∘⋆   ∘ ⋆                                 ∘  │
│           ∘  ∘·⋆   ·              ·· ꙮ                                         │
│     ∘       Xania  ∘    ꙮ∘   ∘   ·✦             Kalon       ⋆   ·              │
│              ·∘·✶        ∘   ∘ Kalura⋆·    ·         ✦     Fenum    ∘    ∘   ⋆ │
│ ∘     ∘      ✶⋆·        ⋆   ⊛     ··     ·        ✧  ⋆⋆ ·  ✦       ⋆           │
│               ∘         ★·✶                        ✧✧ ∘ ⋆   ··✶         ⋆✶     │
│         ⊛       ·      ·  ·                     ·   ⋆       ⋆        Telius    │
│   ∘     ⋆             Pyror·     ∘       ⋆             ∘  ·         ·✶✧✶⋆      │
│                    ░ ✶ ░   ✶      ∘  ∘      ∘                      ░           │
│                      ░··∘·· ∘  ⋆            ·                            ░     │
│·  ·   ✧         ░ · ▒▒  ★                  ✶     ∘                         ·   │
│            ✧      ░·▒▒ ░ ░    ·           ·∘✶              ·         ░ ∘       │
│          ∘  ·  ░✧░░  ▒    ∘          ·   Draix                ∘      ░░        │
│ ✧       ✶      ∘      ░        ∘  ·✦             ∘            ░ · ∘    ░   ∘   │
│        ··          ░      ∘     ··⋆∘     ·               ░       ░ ∘          ∘│
│ ··· · Wyara∘ ⋆       ░  ∘⚡     Morion                     ░░   ░     ▒ ░░ ✦    │
└────────────────────────────────────────────────────────────────────────────────┘
```

### Constellation catalog with lore
```
$ python3 constellation_map.py --catalog-only --seed 777

── Constellation Catalog ──

  1. Pyror, The Forge
      Stars: 8  |  Brightest: mag 0.7
      Notable stars: η (Eta), γ (Gamma), θ (Theta), β (Beta), δ (Delta), ζ (Zeta)
      Scholars of the Obsidian Tower believe Pyror, The Forge marks the Great
      Convergence — when the void serpent first awoke from the edge of reality.

  2. Gorius, The Root
      Stars: 5  |  Brightest: mag 0.7
      ...
```

### JSON export
```
$ python3 constellation_map.py --seed 42 --export atlas.json
Star map exported to atlas.json

$ cat atlas.json | python3 -m json.tool | head -20
{
  "seed": 42,
  "width": 80,
  "height": 40,
  "constellations": [
    {
      "id": 0,
      "name": "Velara",
      "title": "The Tide",
      "full_name": "Velara, The Tide",
      "lore": "Ancient mariners used Velara, The Tide...",
      "stars": [
        { "x": 28.63, "y": 22.7, "magnitude": 2.97, "name": "γ Velara", "greek_letter": "γ (Gamma)" },
        ...
```

## What It Does

1. **Seeds the RNG** — Either from `--seed` or a random value, ensuring reproducibility
2. **Places nebulae** — Scatters 1-5 nebulae across the sky, rendered with ░▒▓ characters at varying densities
3. **Generates constellations** — Picks a random shape type, places 3-9 stars in that pattern, draws connection lines, assigns a procedurally generated name (e.g., "Aethara, The Guardian")
4. **Names the bright stars** — Assigns Greek letter designations (α, β, γ…) to each constellation's brightest stars
5. **Generates lore** — Fills a mythological template with randomized proper nouns to create unique lore for each constellation
6. **Scatters background stars** — Hundreds of randomly placed stars with magnitude-based brightness symbols
7. **Places deep sky objects** — Galaxies (ꙮ), nebulae (⊛), clusters (✺), pulsars (⚡), quasars (✧), and black holes (◎)
8. **Renders the atlas** — Composites everything into a bordered ASCII canvas with legend, constellation catalog, and deep sky object list

## Configuration Options

| Flag | Default | Description |
|------|---------|-------------|
| `--seed` | random | Random seed for reproducible maps |
| `--width` | 80 | Map width in characters |
| `--height` | 40 | Map height in characters |
| `--constellations` | 12 | Number of constellations |
| `--stars` | 200 | Number of background stars |
| `--nebulae` | 3 | Number of nebulae |
| `--deep-objects` | 8 | Number of deep sky objects |
| `--no-color` | off | Disable ANSI color output |
| `--no-lines` | off | Hide constellation connection lines |
| `--no-labels` | off | Hide constellation name labels |
| `--compact` | off | Show only the visual map |
| `--catalog-only` | off | Show only the constellation catalog |
| `--export FILE` | — | Export star map data as JSON |

## Running Tests

```bash
python3 test_constellation_map.py
```

24 tests covering generation, reproducibility, rendering, JSON export, and edge cases.