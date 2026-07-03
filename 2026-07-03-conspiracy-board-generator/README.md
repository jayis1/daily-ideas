# 🔍 Procedural Conspiracy Board Generator

A command-line tool that generates **random conspiracy investigation boards** in ASCII art — complete with entities (people, organizations, events, locations), red-string connections, cryptic notes, evidence tags, and a full legend. Every run produces a unique, paranoid masterpiece.

```
┌──────────────────────────────────────────────────────────────────┐
│       ┌──────────────┐                                          │
│       │TRUST NO ONE  │                                          │
│       └──────┬───────┘                                          │
│              ·                                                  │
│    ◆━━━━━━━━━◈         ┌─────────────────────┐                 │
│ The Syndicate  The Collapse  │IT WAS NEVER A THEORY│               │
│     │SEES    ·    └──────┬──────────────┘                 │
│     ·        ·           ·                                  │
│     ·         ·         ·                                   │
│     ·          ·   ☻━━━━━☻                                  │
│     ·     [DOCUMENT] Mr. Nyx  Dr. Vance                    │
│     ▲              [CIPHER]                                 │
│  Site Alpha                                                   │
│     ·                                                        │
│     ·                                                        │
│     ·        ◆━━━━━━━━━━━▲                                  │
│     └─Division 6   HUNTS   The Bunker                      │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Features

- **Procedural generation** — every board is unique with randomized entities, connections, and notes
- **4 entity types** — People (☻), Organizations (◆), Events (◈), Locations (▲)
- **Connection strings** — Bresenham line-drawn "red strings" with varying thickness (weak/medium/strong)
- **Evidence tags** — randomly assigned evidence types (PHOTO, DOCUMENT, CIPHER, etc.)
- **Cryptic note boxes** — boxed paranoid messages scattered across the board
- **Full legend** — entity roster, connection list, and note index below the board
- **Narrative mode** — generates a classified intelligence briefing from the board data
- **Colored output** — ANSI color support (people=cyan, orgs=magenta, events=yellow, notes=green, strings=red)
- **Reproducible seeds** — use `--seed` to regenerate the same board
- **Configurable size** — control board dimensions and entity counts

## Installation

No external dependencies needed — just Python 3.6+:

```bash
# Clone or download
cd ~/daily-ideas/2026-07-03-conspiracy-board-generator

# Make executable (optional)
chmod +x conspiracy_board.py
```

## Usage

```bash
# Default board (90x45, 5 people, 3 orgs, 3 events, 2 locations)
python3 conspiracy_board.py

# Custom board with narrative briefing
python3 conspiracy_board.py --narrative

# Reproducible board with a seed
python3 conspiracy_board.py --seed 42

# Custom dimensions and entity counts
python3 conspiracy_board.py --width 120 --height 50 --people 6 --orgs 4 --events 4 --connections 15

# Plain text (no ANSI colors) — great for piping to files
python3 conspiracy_board.py --no-color > board.txt

# All options
python3 conspiracy_board.py --help
```

### Command-line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--width` | 90 | Board width in characters |
| `--height` | 45 | Board height in characters |
| `--people` | 5 | Number of people on the board |
| `--orgs` | 3 | Number of organizations |
| `--events` | 3 | Number of events |
| `--locations` | 2 | Number of locations |
| `--connections` | 9 | Number of connections between entities |
| `--notes` | 4 | Number of cryptic notes |
| `--seed` | random | Random seed for reproducibility |
| `--narrative` | off | Also print a classified briefing |
| `--no-color` | off | Disable ANSI color output |

## Examples

### Quick board
```bash
python3 conspiracy_board.py --seed 42
```

### Large board with lots of connections
```bash
python3 conspiracy_board.py --width 120 --height 55 --people 8 --orgs 5 --connections 20 --notes 6
```

### Generate a briefing for a TTRPG session
```bash
python3 conspiracy_board.py --narrative --seed 12345 --no-color > session_briefing.txt
```

### Save a board as text art
```bash
python3 conspiracy_board.py --no-color --seed 7 > my_conspiracy.txt
```

## How It Works

1. **Entity placement**: Entities are placed on a grid with randomized offsets to create organic-looking layouts while avoiding complete overlaps
2. **Connection drawing**: Connections are rendered using Bresenham's line algorithm, with thickness based on connection strength (1=weak dots, 2=medium dashes, 3=strong solid lines)
3. **Note boxes**: Cryptic notes are drawn as boxed text with box-drawing characters
4. **Evidence tags**: Entities randomly receive 0-2 evidence types displayed above their symbol
5. **Legend**: A formatted legend below the board lists all entities, connections, and notes with color coding

## Testing

```bash
python3 test_conspiracy_board.py
```

Runs 21 tests covering entity generation, board rendering, narrative output, reproducibility, and more.

## Use Cases

- **Tabletop RPGs** — Generate conspiracy plots for modern/cyberpunk/investigation campaigns
- **Creative writing prompts** — Use generated boards as story seeds
- **ASCII art fun** — Share paranoid masterpieces with friends
- **Game prototyping** — Use as a starting point for investigation game mechanics