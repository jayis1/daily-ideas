# ✦ Perfume Alchemist

A procedural perfume generator that creates unique, evocative fragrance compositions with note pyramids, scent profile visualizations, harmony scores, side-by-side comparisons, and poetic descriptions — all in your terminal.

## What It Does

Perfume Alchemist generates procedurally unique perfumes using a rich database of 60 real fragrance notes organized into top, heart, and base tiers. Each generated perfume includes:

- **A French-inspired name** (e.g., *Peau d'Âme*, *Cendres et Roses*, *Brume Sans Nom*)
- **Fragrance family** (Chypre, Oriental, Floral, Gourmand, etc.)
- **Mood & season** (enigmatic, opulent, melancholic; eternal spring, monsoon dusk…)
- **Origin story** (a Carpathian monastery, a Venetian palazzo at Carnival…)
- **Note pyramid** — a structured ASCII chart of top → heart → base notes
- **Scent profile bar chart** — visual breakdown by category (floral, woody, spicy…) weighted by note depth
- **Harmony score** — rates how well the note categories complement each other (★★★ Harmonious → ···· Contrarian)
- **Tasting notes** — individual note descriptions
- **Impressions** — a prose description of the fragrance experience

## Features

- 🎲 **Random generation** — millions of unique perfume combinations
- 🏛️ **10 fragrance families** — Chypre, Oriental, Floral, Fresh, Woody, Gourmand, Fougère, Leather, Green, Fruity
- 🎭 **24 moods** — from enigmatic to visceral
- 🌿 **60 real fragrance notes** — 20 each for top, heart, and base
- 📊 **ASCII visualizations** — note pyramid + weighted scent profile bar charts
- 🎨 **Interactive mode** — browse by mood, family, season, or go full random
- 📦 **Collection mode** — generate curated 5-perfume collections
- ⚔️ **Fragrance Duel** — side-by-side comparison of two perfumes, with shared notes and categories
- 🔍 **Note search** — look up any note by name or category across all tiers
- 📐 **Harmony scoring** — algorithmic rating of how well a perfume's note categories harmonize
- 🎯 **Realistic concentrations** — longevity and sillage are now consistent with concentration (EDC lasts less than Extrait)
- 📤 **JSON export** — save perfume compositions to JSON files for sharing or further processing
- 🔒 **Reproducible** — seed flag for deterministic output
- 🆚 **`--version`** — print the version number

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

# Generate a Chypre fragrance (partial/case-insensitive match)
python3 perfume_alchemist.py --generate --family chypre

# Generate a hypnotic fragrance
python3 perfume_alchemist.py --generate --mood hypnotic

# Generate a fragrance for high summer
python3 perfume_alchemist.py --generate --season "high summer"

# Generate a 5-perfume collection with varied families
python3 perfume_alchemist.py --collection

# Compare two random fragrances side by side
python3 perfume_alchemist.py --compare

# Search for notes containing 'oud'
python3 perfume_alchemist.py --search oud

# Search for all citrus notes
python3 perfume_alchemist.py --search citrus

# Export perfume(s) to JSON
python3 perfume_alchemist.py --generate --export my_perfume.json
python3 perfume_alchemist.py --collection --export collection.json
python3 perfume_alchemist.py --compare --export duel.json

# Reproducible output with a seed
python3 perfume_alchemist.py --generate --seed 42

# List available fragrance families
python3 perfume_alchemist.py --list-families

# List available moods
python3 perfume_alchemist.py --list-moods

# List available seasons
python3 perfume_alchemist.py --list-seasons

# Print version
python3 perfume_alchemist.py --version
```

## Usage Examples

### Generate a single perfume
```
$ python3 perfume_alchemist.py --generate --seed 99

✦ Vérité Oublié ✦
  "Fougère" — Barbershop soul — lavender, coumarin, fern-green sophistication.

  Mood: Dreamlike
  Season: Winter solstice
  Origin: A savannah veranda in August
  Concentration: Eau de Cologne
  Longevity: 3–5 hours
  Sillage: Moderate
  Harmony: ★·· Distinctive (27%)

                      ── Note Pyramid ──
╭───────────────────────────────╮
│              TOP              │
│  mint  ·  pink pepper        │
├───────────────────────────────┤
│             HEART             │
│  clove bud · black tea       │
├───────────────────────────────┤
│              BASE             │
│  immortelle · guaiacwood     │
╰───────────────────────────────╯

                     ── Scent Profile ──
  Herbal   ███████░░░░░░░░░░░░░░░░░░░░░░░ 25%
  Spicy    ███████░░░░░░░░░░░░░░░░░░░░░░░ 25%
  Earthy   ███████░░░░░░░░░░░░░░░░░░░░░░░ 25%
  Woody    ███████░░░░░░░░░░░░░░░░░░░░░░░ 25%

                     ── Tasting Notes ──

  ▸ TOP:
    mint — crisp and invigorating, morning garden fresh
    pink pepper — rosy warmth with a playful bite

  ▸ HEART:
    clove bud — arid heat, dental sharp, ancient spice route
    black tea — tannic depth, smoky, contemplative cup

  ▸ BASE:
    immortelle — curry flower, burnt sugar, eternal straw
    guaiacwood — smoky, rose-tinged, quiet strength
```

### Search for notes
```
$ python3 perfume_alchemist.py --search oud

  ── Notes matching 'oud' (1 found) ──

  [Heart] oud (woody) — dark, sacred wood, smoke and mystery
```

### Compare two fragrances
```
$ python3 perfume_alchemist.py --compare

  ══════════════════ FRAGRANCE DUEL ══════════════════

  ✦ Mirage de Minuit     ✦ Mirage Perdu
  Oriental / Amber       Green / Herbaceous
  ...
  Shared categories: Earthy, Green, Herbal
```

## How It Works

1. **Name generation**: Combines French prefixes, suffixes, and standalone poetic names
2. **Note selection**: Randomly selects 2–3 top notes, 2–4 heart notes, and 2–4 base notes from curated pools of real fragrance ingredients, ensuring no duplicates
3. **Family & mood assignment**: Each perfume is assigned a fragrance family and mood that shape its character
4. **Origin & season**: An evocative origin story and seasonal context add narrative depth
5. **Concentration realism**: Longevity and sillage are now drawn from ranges consistent with the concentration level (Eau de Cologne → shorter, Parfum/Extrait → longer)
6. **Harmony scoring**: Note categories are checked against known harmonious pairings (e.g., floral + woody, citrus + herbal) to produce a compatibility score
7. **Description generation**: Procedurally combines the name, notes, mood, origin, and family into evocative prose descriptions using 5 different templates
8. **Visualization**: Renders an ASCII note pyramid and weighted category bar chart for scent profile analysis

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

## Testing

```bash
python3 test_perfume_alchemist.py
```

38 tests cover data integrity, generation, name variety, concentration consistency, harmony scoring, note search, comparison, JSON export, and CLI flags.

## License

MIT