# 🔍 Procedural Conspiracy Board Generator

**Version 2.0.0**

A command-line tool that generates **random conspiracy investigation boards** in ASCII art — complete with entities (people, organizations, events, locations), red-string connections, cryptic notes, evidence tags, suspicion scores, cycle detection, conspiracy timelines, redacted briefings, and a full legend. Every run produces a unique, paranoid masterpiece.

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
│     ·        ◆━━━━━━━━━━━▲                                  │
│     └─Division 6   HUNTS   The Bunker                      │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Features

### Core (v1.0)
- **Procedural generation** — every board is unique with randomized entities, connections, and notes
- **4 entity types** — People (☻), Organizations (◆), Events (◈), Locations (▲)
- **Connection strings** — Bresenham line-drawn "red strings" with varying thickness (weak/medium/strong)
- **Evidence tags** — randomly assigned evidence types (PHOTO, DOCUMENT, CIPHER, etc.)
- **Cryptic note boxes** — boxed paranoid messages scattered across the board
- **Full legend** — entity roster, connection list, and note index below the board
- **Colored output** — ANSI color support (people=cyan, orgs=magenta, events=yellow, notes=green, strings=red)
- **Reproducible seeds** — use `--seed` to regenerate the same board
- **Configurable size** — control board dimensions and entity counts

### New in v2.0
- **Suspicion scores** — each entity gets a computed suspicion level (LOW → MODERATE → HIGH → CRITICAL → EXTREME) based on connections, evidence, and entity-type diversity, displayed with a progress bar in the legend
- **Cycle detection** — automatically detects triangular connection patterns (A→B→C→A) and highlights them in the legend
- **Conspiracy timeline** (`--timeline`) — generates dated, classified timeline events linking entities to key moments with redacted text
- **JSON output** (`--json`) — export all board data (entities, connections, notes, cycles, timeline) as structured JSON for integration with other tools
- **Redacted text** — timeline entries in narratives include █████-style redaction for flavor
- **Narrative improvements** — classified briefing now includes suspicion assessment and strength-of-connection labels (weak/moderate/strong)
- **Better entity placement** — overlap avoidance for both entities and note boxes
- **Input validation** — `--version` flag, board dimension clamping (40–200 × 20–100), entity count validation, and helpful error messages
- **Connection diversity** — connections preferentially form between different entity types for more interesting boards
- **Improved `--help`** — includes usage examples and parameter ranges

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
# Default board (90×45, 5 people, 3 orgs, 3 events, 2 locations)
python3 conspiracy_board.py

# Board with classified briefing narrative
python3 conspiracy_board.py --narrative

# Board with conspiracy timeline
python3 conspiracy_board.py --timeline

# Both narrative and timeline
python3 conspiracy_board.py --narrative --timeline

# Reproducible board with a seed
python3 conspiracy_board.py --seed 42

# JSON output (for scripts, analysis, or integration)
python3 conspiracy_board.py --json --seed 42

# Custom dimensions and entity counts
python3 conspiracy_board.py --width 120 --height 55 --people 8 --orgs 5 --connections 20 --notes 6

# Plain text (no ANSI colors) — great for piping to files
python3 conspiracy_board.py --no-color > board.txt

# Show version
python3 conspiracy_board.py --version

# All options
python3 conspiracy_board.py --help
```

### Command-line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--width` | 90 | Board width in characters (40–200) |
| `--height` | 45 | Board height in characters (20–100) |
| `--people` | 5 | Number of people on the board |
| `--orgs` | 3 | Number of organizations |
| `--events` | 3 | Number of events |
| `--locations` | 2 | Number of locations |
| `--connections` | 9 | Number of connections between entities |
| `--notes` | 4 | Number of cryptic notes |
| `--seed` | random | Random seed for reproducibility |
| `--narrative` | off | Also print a classified briefing |
| `--timeline` | off | Generate and display a conspiracy timeline |
| `--json` | off | Output all board data as JSON |
| `--no-color` | off | Disable ANSI color output |
| `--version` | — | Print version and exit |

## Examples

### Quick board
```bash
python3 conspiracy_board.py --seed 42
```

### Large board with lots of connections
```bash
python3 conspiracy_board.py --width 120 --height 55 --people 8 --orgs 5 --connections 20 --notes 6
```

### Generate a full briefing for a TTRPG session
```bash
python3 conspiracy_board.py --narrative --timeline --seed 12345 --no-color > session_briefing.txt
```

### Export as JSON for analysis
```bash
python3 conspiracy_board.py --json --seed 7 > board_data.json
```

### Save a board as text art
```bash
python3 conspiracy_board.py --no-color --seed 7 > my_conspiracy.txt
```

## How It Works

1. **Entity generation**: Entities are drawn from themed pools (PEOPLE, ORGANIZATIONS, EVENTS, LOCATIONS) and placed on a grid with jittered positions and overlap avoidance
2. **Suspicion scoring**: Each entity's suspicion is computed from connection count (×0.15), connection strength (×0.05), evidence count (×0.1), and the diversity of connected entity types (×0.1 per type)
3. **Connection drawing**: Connections are rendered using Bresenham's line algorithm, with thickness based on connection strength (1=weak dots, 2=medium dashes, 3=strong solid lines). Connections preferentially link different entity types
4. **Note boxes**: Cryptic notes are drawn as boxed text with box-drawing characters, avoiding entity positions
5. **Note labels**: Connection labels appear near the midpoint of each string
6. **Timeline generation**: A conspiracy timeline is built from template sentences, dated across a plausible range (2019–2028), with classification levels and entity references
7. **Cycle detection**: The system checks for triangular connection patterns (A→B→C→A) and reports them in the legend
8. **Legend**: A formatted legend below the board lists all entities (sorted by suspicion), connections (with strength), cryptic notes, and any detected cycles

## Testing

```bash
python3 test_conspiracy_board.py
```

Runs 57 tests covering entity generation, board rendering, narrative output, timeline generation, JSON export, suspicion scoring, cycle detection, redaction, reproducibility, and more.

## Use Cases

- **Tabletop RPGs** — Generate conspiracy plots for modern/cyberpunk/investigation campaigns
- **Creative writing prompts** — Use generated boards as story seeds
- **ASCII art fun** — Share paranoid masterpieces with friends
- **Game prototyping** — Use as a starting point for investigation game mechanics
- **Data pipeline** — Use `--json` output to feed generated conspiracies into other tools or visualizations

## Changelog

### v2.0.0
- **Added**: Suspicion scores for all entities (computed from connections, evidence, and type diversity)
- **Added**: Cycle detection for triangular connection patterns
- **Added**: `--timeline` flag to generate dated conspiracy timeline events with classification levels
- **Added**: `--json` flag for structured JSON output (entities, connections, notes, cycles, timeline)
- **Added**: `--version` flag
- **Added**: Redacted text (█████) in narrative timeline fragments
- **Added**: Connection strength labels (weak/moderate/strong) in narrative
- **Added**: Entity overlap avoidance for better board layout
- **Added**: Note box placement avoidance of entity positions
- **Added**: Connection diversity — connections preferentially link different entity types
- **Added**: Input validation with helpful error messages
- **Added**: Board dimension clamping (40–200 × 20–100)
- **Improved**: Legend now sorts entities by suspicion score with progress bars
- **Improved**: `--help` now includes usage examples
- **Fixed**: `suspicion_label` boundary conditions (correct threshold ranges)
- **Fixed**: Template string variable names (`from_ent`/`to_ent` instead of Python reserved `from`/`to`)

### v1.0.0
- Initial release with procedural board generation, Bresenham strings, evidence tags, cryptic notes, and narrative mode

## License

MIT