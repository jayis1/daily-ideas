# ✦ Perfume Alchemist

A procedural perfume generator that creates unique, evocative fragrance compositions with note pyramids, scent profile visualizations, and poetic descriptions — all in your terminal.

## What It Does

Perfume Alchemist generates procedurally unique perfumes using a rich database of real fragrance notes organized into top, heart, and base tiers. Each generated perfume includes:

- **A French-inspired name** (e.g., *Peau d'Âme*, *Cendres et Roses*, *Brume Sans Nom*)
- **Fragrance family** (Chypre, Oriental, Floral, Gourmand, etc.)
- **Mood & season** (enigmatic, opulent, melancholic; eternal spring, monsoon dusk…)
- **Origin story** (a Carpathian monastery, a Venetian palazzo at Carnival…)
- **Note pyramid** — a structured ASCII chart of top → heart → base notes
- **Scent profile bar chart** — visual breakdown by category (floral, woody, spicy…)
- **Tasting notes** — individual note descriptions
- **Impressions** — a prose description of the fragrance experience

## Features

- 🎲 **Random generation** — millions of unique perfume combinations
- 🏛️ **10 fragrance families** — Chypre, Oriental, Floral, Fresh, Woody, Gourmand, Fougère, Leather, Green, Fruity
- 🎭 **24 moods** — from enigmatic to visceral
- 🌿 **60 real fragrance notes** — 20 each for top, heart, and base
- 📊 **ASCII visualizations** — note pyramid + scent profile bar charts
- 🎨 **Interactive mode** — browse by mood, family, or go full random
- 📦 **Collection mode** — generate curated 5-perfume collections
- 🔒 **Reproducible** — seed flag for deterministic output

## Installation

```bash
# No dependencies needed — pure Python 3.6+
# Just clone and run:
git clone <repo-url>
cd perfume-alchemist
```

## How to Run

```bash
# Interactive mode (default) — menu-driven exploration
python3 perfume_alchemist.py

# Generate a single random perfume
python3 perfume_alchemist.py --generate

# Generate 3 perfumes
python3 perfume_alchemist.py --generate 3

# Generate a Chypre fragrance
python3 perfume_alchemist.py --generate --family Chypre

# Generate a hypnotic fragrance
python3 perfume_alchemist.py --generate --mood hypnotic

# Generate a 5-perfume collection with varied families
python3 perfume_alchemist.py --collection

# Reproducible output with a seed
python3 perfume_alchemist.py --generate --seed 42

# List available fragrance families
python3 perfume_alchemist.py --list-families

# List available moods
python3 perfume_alchemist.py --list-moods
```

## Usage Examples

### Generate a single perfume
```
$ python3 perfume_alchemist.py --generate

                    ✦ Ombre Sauvage ✦                    
  "Leather / Tobacco" — By the fire — saddle leather, pipe smoke, vintage study.

  Mood: Hypnotic
  Season: Monsoon dusk
  Origin: A Marrakech souk at closing time
  Concentration: Eau de Parfum
  Longevity: 8–12 hours
  Sillage: Room-filling

                      ── Note Pyramid ──                    
╭──────────────────────────────────────────────────────╮
│                          TOP                         │
│  saffron  ·  bergamot  ·  pink pepper               │
├──────────────────────────────────────────────────────┤
│                         HEART                        │
│  oud · iris butter · cinnamon bark                   │
├──────────────────────────────────────────────────────┤
│                          BASE                         │
│  leather accord · ambergris · vetiver haiti          │
╰──────────────────────────────────────────────────────╯

                     ── Scent Profile ──                    
  Spicy     ███████░░░░░░░░░░░░░░░░░░░░░░░ 25%
  Woody      █████░░░░░░░░░░░░░░░░░░░░░░░░░ 17%
  Floral     ███░░░░░░░░░░░░░░░░░░░░░░░░░░░ 17%
  Animalic   ███░░░░░░░░░░░░░░░░░░░░░░░░░░░ 17%
  Earthy     ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 8%
  Leather    ██░░░░░░░░░░░░░░░░░░░░░░░░░░░ 8%
  Citrus     ██░░░░░░░░░░░░░░░░░░░░░░░░░░░ 8%

  ▸ TOP:
    saffron — liquid gold, hay-like, ancient luxury
    bergamot — bright, sparkling citrus that dances on first spray
    pink pepper — rosy warmth with a playful bite

  ▸ HEART:
    oud — dark, sacred wood, smoke and mystery
    iris butter — powdery elegance, suede-like violet grace
    cinnamon bark — warm, baking, skin-like comfort

  ▸ BASE:
    leather accord — saddle, smoking jacket, tannery romance
    ambergris — oceanic, saline, warm skin after the sea
    vetiver haiti — dark roots, smoke, rain-soaked earth
```

### Generate by mood
```
$ python3 perfume_alchemist.py --generate --mood sensual
```

### Generate a collection
```
$ python3 perfume_alchemist.py --collection
```

## How It Works

1. **Name generation**: Combines French prefixes, suffixes, and standalone poetic names
2. **Note selection**: Randomly selects 2-3 top notes, 2-4 heart notes, and 2-4 base notes from curated pools of real fragrance ingredients, ensuring no duplicates
3. **Family & mood assignment**: Each perfume is assigned a fragrance family and mood that shape its character
4. **Origin & season**: A evocative origin story and seasonal context add narrative depth
5. **Description generation**: Procedurally combines the name, notes, mood, origin, and family into evocative prose descriptions
6. **Visualization**: Renders an ASCII note pyramid and category bar chart for scent profile analysis

## Fragrance Families

| Family | Character |
|--------|-----------|
| Chypre | Bergamot on oakmoss, earthy elegance |
| Oriental / Amber | Vanilla, oud, and spice bazaars |
| Floral | Roses, jasmines, bouquets in bloom |
| Fresh / Aquatic | Sea spray and ozone, open horizons |
| Woody / Aromatic | Cedar, vetiver, incense smoke |
| Gourmand | Vanilla, coffee, dark chocolate |
| Fougère | Lavender, coumarin, fern-green |
| Leather / Tobacco | Saddle leather, pipe smoke |
| Green / Herbaceous | Crushed stems, fresh-cut grass |
| Fruity / Tropical | Mango, coconut, sun-drenched abandon |

## License

MIT