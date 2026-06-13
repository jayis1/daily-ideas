# ✨ CLI Tarot Reader ✨

A beautifully rendered terminal tarot card reader with ASCII art cards, multiple spreads, full interpretations, and dramatic reveal animations. Pull cards from a complete 78-card Rider-Waite–style deck — all 22 Major Arcana and 56 Minor Arcana — right from your command line.

![Tarot](https://img.shields.io/badge/type-divination-9370DB) ![Python](https://img.shields.io/badge/python-3.8+-green) ![CLI](https://img.shields.io/badge/interface-CLI-blue)

## Features

- **Full 78-card deck** — All 22 Major Arcana with unique ASCII art, plus 56 Minor Arcana (Wands, Cups, Swords, Pentacles) with suit-specific art
- **5 spread types** — Single Card, Three Card (Past/Present/Future), Celtic Cross (10 cards), Relationship Spread (8 cards), Decision Spread (7 cards)
- **ASCII art card rendering** — Each Major Arcana card has hand-crafted ASCII art displayed in a bordered card frame
- **Reversed cards** — ~30% chance of reversal, with reversed meanings and flipped art
- **Narrative interpretations** — Every card has both keyword meanings and a poetic "story" interpretation
- **Elemental synthesis** — After a reading, the tool analyzes the elemental balance (Fire/Water/Air/Earth) and provides a synthesized interpretation
- **Card browser** — Explore the full deck interactively, suit by suit
- **Card of the Day** — Quick daily draw with meaning and story
- **Dramatic animations** — Slow-print reveals and dramatic pauses for an atmospheric reading experience
- **Non-interactive mode** — Pipe-friendly quick readings for scripts and cron jobs

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

### Card of the Day (non-interactive)

```bash
python3 tarot_reader.py --daily
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
```

## What It Does

The tarot reader simulates a complete Rider-Waite–style tarot deck reading:

1. **Deck creation** — Builds all 78 cards (22 Major + 56 Minor Arcana) with meanings, stories, and ASCII art
2. **Card drawing** — Randomly selects cards with proper shuffling (no duplicates within a reading), with ~30% chance of reversal
3. **Card rendering** — Displays each card in a framed ASCII art layout with name, orientation, keywords, and narrative
4. **Reading synthesis** — After drawing all cards, analyzes the spread's overall energy: upright/reversed balance, Major Arcana presence, and elemental distribution (Fire/Water/Air/Earth)
5. **Interactive browsing** — Explore every card in the deck, view both upright and reversed meanings

The readings are for entertainment and reflection. The real magic is what you bring to the interpretation.