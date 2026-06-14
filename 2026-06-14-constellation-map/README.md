# ✦ Constellation Map — Procedural Star Atlas Generator

A command-line tool that generates rich, navigable ASCII star maps with procedurally created constellations, mythical names, deep sky objects, nebulae, meteor showers, and lore. Every map is unique — seeded by your choice or left to chance.

## Features

- **Procedural constellation generation** — 6 distinct shapes (chain, triangle, cross, arc, cluster, spiral) with randomly generated mythological names and titles
- **Greek letter star designations** — Brightest stars in each constellation get proper α, β, γ… labels
- **Nebulae** — Colored ASCII nebulae (░▒▓) that cloud regions of the sky
- **Deep sky objects** — Galaxies (ꙮ), pulsars (⚡), quasars (✧), black holes (◎), star clusters (✺), and more
- **Meteor showers** — Procedurally generated meteor shower streaks with radiant points, intensity, and flavor text
- **Rich lore engine** — Template-based lore generator fills in mythological stories for each constellation
- **Coordinate grid overlay** — Optional `--grid` flag shows ┊┄ grid lines with coordinate markers
- **Constellation search** — `--find` flag to search constellations by name or title (case-insensitive)
- **Map statistics** — `--stats` flag shows star counts, density, brightest magnitude, and more
- **Interactive navigation** — `--interactive` mode with arrow-key cursor, per-position info display
- **Reproducible maps** — Use `--seed` to generate the exact same map every time
- **JSON export** — Export the full star catalog (including meteor showers and statistics) as structured JSON
- **Per-character ANSI colors** — Full color support with color-coded stars, nebulae, meteor streaks, labels, and deep objects
- **Configurable rendering** — Toggle colors, constellation lines, labels, meteor showers, and grid
- **`--version` and `--help` flags** — Standard CLI flags

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

# Hide meteor shower streaks
python3 constellation_map.py --no-meteors

# Show coordinate grid overlay
python3 constellation_map.py --grid

# Compact output — just the visual map, no catalog
python3 constellation_map.py --compact

# Show only the constellation catalog (no visual map)
python3 constellation_map.py --catalog-only

# Search for constellations by name or title
python3 constellation_map.py --find Phoenix

# Show map statistics
python3 constellation_map.py --stats

# Launch interactive navigation mode
python3 constellation_map.py --interactive

# Export star data as JSON
python3 constellation_map.py --export atlas.json

# Show version
python3 constellation_map.py --version
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

### Search for constellations
```
$ python3 constellation_map.py --find Phoenix --no-color

── Search Results (2 found) ──

  Lumix, The Phoenix
      Stars: 7  |  Brightest: mag 1.0
      Center: (48.1, 17.4)
      Lumix, The Phoenix is brightest during spring dawn, when legend says
      the griffin wakes once more and the crystal scepter shines with
      renewed brilliance.

  Pyrion, The Phoenix
      Stars: 7  |  Brightest: mag 1.1
      Center: (58.1, 9.4)
      The Nyssians tell of Pyrion, The Phoenix — a griffin that races
      across the heavens each autumn equinox, leaving a trail of ethereal mist.
```

### Map statistics
```
$ python3 constellation_map.py --seed 42 --stats --no-color

── Map Statistics ──

  Total stars:           284
  Constellation stars:   84
  Background stars:      200
  Constellations:        12
  Nebulae:               3
  Deep sky objects:       8
  Meteor showers:        2
  Brightest magnitude:   0.51
  Avg connections:       6.00
  Avg stars/constellation: 7.00
  Map area:             3200 chars²
  Star density:         0.0887 stars/char²
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
      "name": "Ianon",
      "title": "The Void",
      "full_name": "Ianon, The Void",
      "lore": "The oracle of Duskfall once prophesied...",
      "stars": [
        { "x": 33.69, "y": 11.56, "magnitude": 1.15, "name": "β Ianon", "greek_letter": "β (Beta)" },
        ...
      ],
      "connections": [[0, 1], [1, 2], ...]
    },
    ...
  ],
  "meteor_showers": [
    { "name": "Aethonid", "radiant_x": 12.5, "radiant_y": 8.3, "angle": 245.0, "intensity": 12, ... }
  ],
  "statistics": {
    "total_stars": 284,
    "star_density": 0.0887,
    ...
  }
}
```

## What It Does

1. **Seeds the RNG** — Either from `--seed` or a random value, ensuring reproducibility
2. **Places nebulae** — Scatters nebulae across the sky, rendered with ░▒▓ characters at varying densities
3. **Generates constellations** — Picks a random shape type, places 3-9 stars in that pattern, draws connection lines, assigns a procedurally generated name (e.g., "Aethara, The Guardian")
4. **Names the bright stars** — Assigns Greek letter designations (α, β, γ…) to each constellation's brightest stars
5. **Generates lore** — Fills a mythological template with randomized proper nouns to create unique lore for each constellation
6. **Scatters background stars** — Hundreds of randomly placed stars with magnitude-based brightness symbols
7. **Places deep sky objects** — Galaxies (ꙮ), nebulae (⊛), clusters (✺), pulsars (⚡), quasars (✧), and black holes (◎)
8. **Generates meteor showers** — Procedural streaks from radiant points with intensity and peak-activity flavor text
9. **Renders the atlas** — Composites everything into a bordered ASCII canvas with legend, constellation catalog, deep sky object list, and meteor shower data

## Configuration Options

| Flag | Default | Description |
|------|---------|-------------|
| `--version` | — | Show version and exit |
| `--seed` | random | Random seed for reproducible maps |
| `--width` | 80 | Map width in characters |
| `--height` | 40 | Map height in characters |
| `--constellations` | 12 | Number of constellations |
| `--stars` | 200 | Number of background stars |
| `--nebulae` | 3 | Number of nebulae |
| `--deep-objects` | 8 | Number of deep sky objects |
| `--meteor-showers` | 2 | Number of meteor showers |
| `--no-color` | off | Disable ANSI color output |
| `--no-lines` | off | Hide constellation connection lines |
| `--no-labels` | off | Hide constellation name labels |
| `--no-meteors` | off | Hide meteor shower streaks |
| `--grid` | off | Show coordinate grid overlay |
| `--compact` | off | Show only the visual map |
| `--catalog-only` | off | Show only the constellation catalog |
| `--find QUERY` | — | Search constellations by name or title |
| `--stats` | off | Show map statistics |
| `--interactive` | off | Launch interactive navigation mode |
| `--export FILE` | — | Export star map data as JSON |

## Running Tests

```bash
python3 test_constellation_map.py
```

49 tests covering generation, reproducibility, rendering, JSON export, meteor showers, search, statistics, interactive navigator, edge cases (zero counts), color rendering, and more.