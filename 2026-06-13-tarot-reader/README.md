# ✨ CLI Tarot Reader ✨

A beautifully rendered terminal tarot card reader with ASCII art cards, multiple spreads, astrological associations, full interpretations, and dramatic reveal animations. Pull cards from a complete 78-card Rider-Waite–style deck — all 22 Major Arcana and 56 Minor Arcana — right from your command line.

![Tarot](https://img.shields.io/badge/type-divination-9370DB) ![Python](https://img.shields.io/badge/python-3.8+-green) ![CLI](https://img.shields.io/badge/interface-CLI-blue) ![Version](https://img.shields.io/badge/version-1.1.0-orange)

## Features

### Core
- **Full 78-card deck** — All 22 Major Arcana with unique ASCII art, plus 56 Minor Arcana (Wands, Cups, Swords, Pentacles) with suit-specific art
- **5 spread types** — Single Card, Three Card (Past/Present/Future), Celtic Cross (10 cards), Relationship Spread (8 cards), Decision Spread (7 cards)
- **ASCII art card rendering** — Each Major Arcana card has hand-crafted ASCII art displayed in a bordered card frame
- **Reversed cards** — Configurable reversal rate (default 30%), with reversed meanings and flipped art
- **Narrative interpretations** — Every card has both keyword meanings and a poetic "story" interpretation

### Astrology & Analysis
- **Astrological associations** — Major Arcana cards include zodiac signs, ruling planets, and numerological meanings based on Golden Dawn / Rider-Waite correspondences
- **Elemental synthesis** — After a reading, the tool analyzes the elemental balance (Fire/Water/Air/Earth) using both Minor Arcana suits and Major Arcana astrological data
- **Zodiac compatibility** — Relationship spreads include elemental compatibility analysis between "You" and "The Other" cards

### CLI & Integration
- **Card lookup** — Search any card by name with `--card "Death"` (partial match, case-insensitive)
- **Seeded readings** — Reproducible readings with `--seed 42` — same seed, same cards
- **JSON output** — Machine-readable readings with `--json` for scripts, APIs, and piping
- **Save to file** — `--save reading.txt` writes the reading output to disk
- **Configurable reversal rate** — `--reversal-rate 0.5` lets you tune how often cards appear reversed
- **`--version` and `--help`** — Standard CLI flags included
- **Non-interactive mode** — Pipe-friendly quick readings for scripts and cron jobs

### Experience
- **Dramatic animations** — Slow-print reveals and dramatic pauses for an atmospheric reading experience
- **Card browser** — Explore the full deck interactively, suit by suit, with both upright and reversed meanings
- **Card of the Day** — Quick daily draw with meaning and story

## How to Install

No external dependencies — just Python 3.8+:

```bash
# Clone and run directly
git clone <repo-url>
cd tarot-reader
python3 tarot_reader.py
```

Or make it executable:

```bash
chmod +x tarot_reader.py
./tarot_reader.py
```

## How to Run

### Interactive Mode (default)

```bash
python3 tarot_reader.py
```

This launches a full interactive session where you can:
1. Choose a spread and get a full reading with card-by-card reveals
2. Draw your Card of the Day
3. Browse the entire deck (Major Arcana + each suit)

### Quick Reading (non-interactive)

```bash
# Three-card spread
python3 tarot_reader.py --quick

# Celtic Cross spread
python3 tarot_reader.py --quick --spread cross

# Relationship spread
python3 tarot_reader.py --quick --spread relationship

# Decision spread
python3 tarot_reader.py --quick --spread decision
```

### Card of the Day

```bash
python3 tarot_reader.py --daily
```

### Card Lookup

```bash
# Look up a specific card by name (partial match)
python3 tarot_reader.py --card "Death"
python3 tarot_reader.py --card "3 of Cups"
python3 tarot_reader.py --card "queen of wands"
```

### Seeded / Reproducible Readings

```bash
# Same seed always draws the same cards
python3 tarot_reader.py --quick --seed 42
python3 tarot_reader.py --daily --seed 42
```

### JSON Output

```bash
# Machine-readable output for scripts
python3 tarot_reader.py --quick --json
python3 tarot_reader.py --daily --json --seed 7
python3 tarot_reader.py --card "Fool" --json
```

### Save to File

```bash
python3 tarot_reader.py --quick --save my_reading.txt
python3 tarot_reader.py --quick --json --save my_reading.json
```

### Advanced Options

```bash
# All Major Arcana only
python3 tarot_reader.py --quick --major-only

# Adjust reversal rate (0.0 = never reversed, 1.0 = always reversed)
python3 tarot_reader.py --quick --reversal-rate 0.5

# Show version
python3 tarot_reader.py --version
```

### Available Spreads

| Spread | Cards | Flag |
|--------|-------|------|
| Single Card | 1 | `--spread single` |
| Three Card (Past/Present/Future) | 3 | `--spread three_card` |
| Celtic Cross | 10 | `--spread cross` |
| Relationship | 8 | `--spread relationship` |
| Decision | 7 | `--spread decision` |

## Usage Examples

```bash
# Quick three-card reading
$ python3 tarot_reader.py --quick
✨ Three Card Spread ✨
Date: 2026-06-13 03:19

Past: 💧 3 of Cups (Reversed)
  → Blocked or distorted creation in the realm of emotions...
  The creation is blocked in the realm of emotions...

Present: 🔥 1 of Wands (Upright)
  → New beginnings, opportunity, potential, raw energy in the realm of passion...
  The energy of new beginnings flows through the realm of passion...

Future: 🌬 Queen of Swords (Reversed)
  → Insecurity, jealousy, emotional manipulation, dependence in the realm of intellect...

# Daily card
$ python3 tarot_reader.py --daily
✨ Card of the Day ✨
💀 Death (Upright)
  Keywords: Endings, change, transformation, transition, rebirth
  The old self crumbles to make way for the new...

# Card lookup with astrological data
$ python3 tarot_reader.py --card "Death"

✨ 💀 Death ✨
  ┌──────────────────────────────────────────┐
  │                 Upright                   │
  ├──────────────────────────────────────────┤
  │ 💀                Death                💀 │
  ├──────────────────────────────────────────┤
  │               ╭────╮                     │
  │              ╭│ 💀 │╮                     │
  │              │╰──╭╯│                      │
  │              │  ║  │                       │
  │              ╰╮  ╭╯                        │
  │               │🌱│                         │
  │              ╰─╯╰─╯                        │
  ├──────────────────────────────────────────┤
  ...

  ✦ Astrology:
    Zodiac: Scorpio
    Element: Water
    Numerology: 13 (Transformation, rebirth)

# JSON output
$ python3 tarot_reader.py --quick --json --seed 42
{
  "spread": "Three Card Spread",
  "date": "2026-06-13T03:22:42.621663",
  "seed": 42,
  "cards": [
    {
      "position": "Past",
      "name": "Temperance",
      "emoji": "🏺",
      "orientation": "Reversed",
      "meaning": "Imbalance, excess, self-healing...",
      "astrology": {"zodiac": "Sagittarius", "planet": "—", "element": "Fire", ...}
    },
    ...
  ]
}
```

## What It Does

The tarot reader simulates a complete Rider-Waite–style tarot deck reading:

1. **Deck creation** — Builds all 78 cards (22 Major + 56 Minor Arcana) with meanings, stories, ASCII art, and astrological associations
2. **Card drawing** — Randomly selects cards with proper shuffling (no duplicates within a reading), with configurable reversal probability
3. **Card rendering** — Displays each card in a framed ASCII art layout with name, orientation, keywords, and narrative
4. **Reading synthesis** — After drawing all cards, analyzes the spread's overall energy: upright/reversed balance, Major Arcana presence, elemental distribution (Fire/Water/Air/Earth), and astrological influences
5. **Relationship compatibility** — For relationship spreads, analyzes the elemental compatibility between the "You" and "The Other" positions using zodiac element pairs
6. **Interactive browsing** — Explore every card in the deck, view both upright and reversed meanings
7. **Card lookup** — Search for any card by partial name to view its full details and astrological data
8. **JSON output** — Machine-readable format for integration with other tools, scripts, or APIs
9. **Seeded readings** — Reproducible readings for testing, journaling, or sharing

## Testing

```bash
python3 test_tarot_reader.py
```

Runs 23 tests covering deck creation, seeded draws, card lookup, rendering, synthesis, JSON output, and more.

The readings are for entertainment and reflection. The real magic is what you bring to the interpretation.