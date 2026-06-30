# ✦ Perfume Alchemist

A procedural perfume generator that creates unique, evocative fragrance compositions with note pyramids, scent profile visualizations, harmony scores, side-by-side comparisons, and poetic descriptions — all in your terminal.

**Version 1.2.0** — Bug fix release

## What It Does

Perfume Alchemist generates procedurally unique perfumes using a rich database of 60 real fragrance notes organized into top, heart, and base tiers. Each generated perfume includes:

- **A French-inspired name** (e.g., *Peau d'Âme*, *Cendres et Roses*, *Absinthe*, *Brume*)
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
- 🎯 **Realistic concentrations** — longevity and sillage are consistent with concentration (EDC lasts less than Extrait)
- 📤 **JSON export** — save perfume compositions to JSON files for sharing or further processing
- 🔒 **Reproducible** — seed flag for deterministic output
- 🆚 **`--version`** — print the version number
- 📝 **Grammar-correct descriptions** — uses "an" before vowel-starting moods, preserves proper noun capitalization in origins

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
$ python3 perfume_alchemist.py --generate --seed 42

                    ✦ Mirage de Minuit ✦
  "Oriental / Amber" — Warm, resinous, addictive — vanilla, oud, and spice bazaars.

  Mood: Enigmatic
  Season: Monsoon dusk
  Origin: A Bombay spice warehouse at dawn
  Concentration: Eau de Cologne
  Longevity: 2–4 hours
  Sillage: Intimate
  Harmony: ★·· Distinctive (27%)

                      ── Note Pyramid ──
╭───────────────────────────────────╮
│                TOP                │
│  lavender  ·  mastic              │
├───────────────────────────────────┤
│               HEART               │
│  jasmine sambac · magnolia        │
├───────────────────────────────────┤
│                BASE               │
│  balsam peru · vetiver haiti      │
╰───────────────────────────────────╯

                     ── Scent Profile ──
  Floral     ██████████░░░░░░░░░░░░░░░░░░░░ 33%
  Resinous   ███████░░░░░░░░░░░░░░░░░░░░░░░ 25%
  Earthy     ███████░░░░░░░░░░░░░░░░░░░░░░░ 25%
  Herbal     ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 8%
  Green      ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 8%
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

  ✦ Chimère Oublié        ✦ L'Heure Bleue
  Oriental / Amber         Gourmand
  Mood: dreamlike          Mood: nostalgic
  ...
```

## How It Works

1. **Name generation**: Combines French prefixes, suffixes, and standalone poetic names in three distinct styles (prefix+suffix, standalone, prefix-only)
2. **Note selection**: Randomly selects 2–3 top notes, 2–4 heart notes, and 2–4 base notes from curated pools of real fragrance ingredients, ensuring no duplicates
3. **Family & mood assignment**: Each perfume is assigned a fragrance family and mood that shape its character
4. **Origin & season**: An evocative origin story and seasonal context add narrative depth
5. **Concentration realism**: Longevity and sillage are drawn from ranges consistent with the concentration level (Eau de Cologne → shorter, Parfum/Extrait → longer)
6. **Harmony scoring**: Note categories are checked against known harmonious pairings (e.g., floral + woody, citrus + herbal) to produce a compatibility score
7. **Description generation**: Procedurally combines the name, notes, mood, origin, and family into evocative prose descriptions using 5 different templates, with correct a/an grammar
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

47 tests cover data integrity, generation, name variety, concentration consistency, harmony scoring, note search, comparison, JSON export, CLI flags, a/an grammar, origin capitalization, note pyramid alignment, and comparison column alignment.

## Changelog

### v1.2.0 (Bug Fix Release)

- **Fixed: `generate_name()` had two identical branches** — The third name style (style > 0.65) was identical to the first (style < 0.35), both producing "prefix + suffix" names. Now the third branch produces prefix-only names (e.g., "Noir", "Absinthe", "Brume"), giving a proper ~35/30/35 distribution across three distinct styles.
- **Fixed: Duplicate "Velours" in `NAME_PREFIXES`** — The prefix "Velours" appeared twice, giving it double probability. Removed the duplicate.
- **Fixed: "a"/"an" grammar error in descriptions** — All five description templates used "a {mood}" regardless of whether the mood started with a vowel, producing phrases like "a enigmatic", "a opulent". Added `_article()` helper and updated all templates to use correct articles ("an enigmatic", "an opulent").
- **Fixed: Origin capitalization mangled proper nouns** — `str.capitalize()` lowercased all characters after the first, turning "a Parisian attic" into "A parisian attic" and "a Kyoto temple" into "A kyoto temple". Added `_title_case()` function that preserves proper noun capitalization.
- **Fixed: Note pyramid had inconsistent line widths** — Content lines were 1 character shorter than border lines (54 vs 55 chars) due to `.ljust(w+1)` instead of `.ljust(w+2)`. Fixed to use `.ljust(w+2)` so all lines in the pyramid are the same width.
- **Fixed: Compare alignment was broken** — `compare_perfumes()` used perfume name length as the column width for all fields, causing misaligned columns when label lengths varied (e.g., "Harmony: " is 9 chars but "Conc: " is 6). Rewrote to compute column width from actual label+value content, ensuring proper alignment.
- **Fixed: `--generate 0` and `--generate -1` silently succeeded** — Now returns an error: "count must be a positive integer".
- **Fixed: `--export` without generation flag fell through to interactive mode** — Now returns an error requiring `--generate`, `--collection`, or `--compare`.

## License

MIT