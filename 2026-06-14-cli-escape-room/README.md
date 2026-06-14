# 🚪 CLI Escape Room

**v2.0.0** — A fully interactive text-based escape room game for your terminal. Wake up in a locked cell with no memory. Explore rooms, collect items, solve interconnected puzzles, and escape a mysterious underground facility.

## Description

You wake up in a concrete cell. No idea how you got here. The door is locked. A faint hum echoes through the walls. Somewhere beyond these walls lies freedom — but only if you can solve the puzzles that stand between you and the exit.

**CLI Escape Room** is a richly detailed text adventure with 6 interconnected rooms, 13 collectible items, and multiple puzzle chains that must be solved in sequence. Every item has a purpose, every clue connects to something, and the story of *Project Mnemosyne* unfolds as you explore.

## Features

### Core Gameplay
- **6 rooms**: Cell, Corridor, Study, Laboratory, Hidden Passage, Control Room
- **13 items**: Keys, wires, notes, tools, a flashlight, a mysterious gem, and more
- **Interconnected puzzle chains**:
  - 🔑 Find the rusty key → unlock the cell door
  - 🔦 Get the screwdriver → open the desk drawer → get the cabinet key → unlock the filing cabinet → get the flashlight
  - 📝 Find both note fragments → combine them → learn the safe combination → open the safe → get the gem & ID card
  - ⏰ Examine the grandfather clock → discover the keypad code (3333)
  - 🔌 Collect wires → connect them to the electrical panel → restore power
  - 🛢️ Find the oil can → loosen the vent grate → retrieve the ID card
  - 🚪 Swipe ID card + place gem → unlock the exit door → ESCAPE!
- **Dark rooms** that require a flashlight to navigate
- **Locked doors** with different puzzle types (keys, keypads, item requirements)
- **Combination codes** to enter (keypad, safe, cabinet)
- **Atmospheric narrative** with typewriter-style text output
- **Random ambient messages** that enhance immersion in each room

### New in v2.0.0
- **Save/Load system** — persist your progress to `~/.cli-escape-room/save.json` and resume later. The game detects saves on startup and offers to resume.
- **Contextual hint system** — type `hint` at any time for a smart, state-aware hint based on your current room, inventory, and puzzle progress.
- **Scoring & ranking** — your escape is scored based on moves, time, and items found. Earn ranks from F ("Barely Made It") to S ("Master Escapist").
- **Drop/pickup items** — type `drop <item>` to leave an item in a room, and `take <item>` to pick up previously dropped items.
- **Command history** — type `history` to review your last 20 commands.
- **Status display** — type `status` to see your current room, moves, time elapsed, and item count.
- **Save on quit** — when quitting, the game offers to save your progress.
- **Direction shortcuts** — `n`/`s`/`e`/`w` work as shortcuts for north/south/east/west.
- **`--help` and `--version` CLI flags** — standard command-line interface.
- **Improved error handling** — robust handling of EOF, keyboard interrupts, and edge cases.
- **93 unit tests** covering game logic, puzzle walkthrough, save/load, scoring, parsing, hints, and data integrity.

## Installation

No dependencies required — uses only Python 3 standard library.

```bash
# Clone or download
cd ~/daily-ideas/2026-06-14-cli-escape-room
```

## How to Run

```bash
# Start the game
python3 escape_room.py

# Show version
python3 escape_room.py --version

# Show help
python3 escape_room.py --help
```

If a saved game exists, you'll be prompted to resume, start a new game, or delete the save.

## Usage

### Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `look [thing]` | `l`, `examine`, `inspect`, `check` | Look around or examine something specific |
| `go <direction>` | `move`, `walk`, `enter`, `n`/`s`/`e`/`w` | Move to another room |
| `take <item>` | `get`, `grab`, `pick up` | Pick up an item |
| `drop <item>` | `leave`, `discard` | Drop an item in the current room |
| `use <item> on <thing>` | `apply`, `insert`, `connect`, `swipe` | Use an item on something |
| `combine <things>` | `join`, `merge` | Combine items (e.g., note fragments) |
| `inventory` | `i`, `inv`, `items` | Show your inventory |
| `hint` | — | Get a contextual hint for your current situation |
| `status` | — | Show room, moves, time, and item count |
| `save` | — | Save game to disk |
| `load` | — | Load saved game from disk |
| `history` | `log` | Show recent command history |
| `help` | `h`, `?` | Show command help |
| `quit` | `exit`, `q` | Quit the game (offers to save) |

### Example Session

```
▸ What do you do? look
You wake up on a cold metal bed, head pounding...
You notice: Rusty Key, Torn Note (Left Half)
There's A battered metal desk with one drawer.
There's A brick near the floor that sticks out slightly.
Exits: north → The Corridor [LOCKED], east → Hidden Passage

▸ What do you do? take rusty key
You pick up the Rusty Key.

▸ What do you do? use rusty key on padlock
The rusty key fits! The padlock clatters to the floor.

▸ What do you do? n
You head north...
[Corridor description]

▸ What do you do? hint
💡 Hint: The keypad needs a 4-digit code. Examine things that show numbers — the clock seems important.

▸ What do you do? look at clock
The clock is ornate, with carved mahogany. The face reads 3:33.
You notice '3333' etched into the back panel...
You take: Old Photograph

▸ What do you do? keypad
The keypad display blinks, waiting for a 4-digit code.
    ▸ Enter 4-digit code: 3333
✓ ACCESS GRANTED!

▸ What do you do? status
┌─ STATUS ──────────────────────────────────────────────────────┐
│  Room:  The Corridor                                          │
│  Moves: 5                                                     │
│  Time:  2m 14s                                                │
│  Items: 3                                                     │
└────────────────────────────────────────────────────────────────┘

▸ What do you do? save
Game saved! You can resume later with 'load'.
```

### Scoring & Ranks

Your escape is scored on multiple factors:

| Factor | Points |
|--------|--------|
| Base score | 1000 |
| Per move | −5 |
| Per second elapsed | −2 |
| Per item found | +50 |
| All 13 items found bonus | +200 |
| Under 5 minutes bonus | +100 |
| Under 10 moves bonus | +50 |

**Rank tiers:**

| Score | Rank |
|-------|------|
| 1500+ | S — Master Escapist |
| 1200+ | A — Expert Puzzler |
| 900+ | B — Skilled Explorer |
| 600+ | C — Capable Survivor |
| 300+ | D — Lucky Escapee |
| <300 | F — Barely Made It |

### Puzzle Hints (Spoilers!)

<details>
<summary>Click to reveal hints</summary>

1. **Cell door**: Use the rusty key on the padlock
2. **Keypad code**: Examine the grandfather clock carefully — the code is hidden in plain sight
3. **Safe combination**: Find both note fragments and combine them to learn: Right 7, Left 3, Right 9
4. **Filing cabinet**: You need a key with a leaf-shaped handle — check the cell desk with a screwdriver
5. **Lab cabinet code**: The wall markings in the hidden passage say "4-7-2"
6. **Electrical panel**: Connect red wire to RED terminal, blue wire to BLUE terminal
7. **Vent grate**: Oil loosens rust — find the oil can in the lab cabinet
8. **Exit door**: You need both the ID card and the mysterious gem — the console has a card reader and gem slot
9. **Dark rooms**: Get the flashlight from the study filing cabinet before entering the control room
10. **Stuck?**: Type `hint` at any time for a contextual clue

</details>

## Map

```
                    ┌──────────────┐
                    │  CONTROL     │
                    │  ROOM (dark) │
                    │  EXIT →      │
                    └──────┬───────┘
                           │ [keypad: 3333]
                    ┌──────┴───────┐
         ┌─────────┤  CORRIDOR   ├─────────┐
         │         │  Clock 3:33 │         │
         │         └──────┬───────┘         │
    ┌────┴────┐           │           ┌────┴────┐
    │  STUDY  │     ┌─────┴─────┐     │  LAB    │
    │ Safe    │     │   CELL    │     │ Panel   │
    │ Cabinet │     │  Padlock  │     │ Cabinet │
    └─────────┘     └─────┬─────┘     └─────────┘
                          │
                   ┌──────┴──────┐
                   │   HIDDEN    │
                   │   PASSAGE   │
                   │  Shelf/Vent │
                   └─────────────┘
```

## What It Does

The game implements a complete escape room experience in pure Python with no external dependencies:

- **Game engine**: Room navigation, inventory management, drop/pickup system, puzzle state tracking via flags, locked door system
- **Parser**: Natural-ish command processing with aliases, direction shortcuts (n/s/e/w), and multi-word commands (pick up, look at)
- **Puzzle system**: Multiple puzzle types — key locks, combination locks, code keypads, item-on-object interactions, item combination, dark room mechanics
- **Hint engine**: Context-aware hints that analyze current room, inventory, flags, and locked doors to suggest the most relevant next step
- **Save system**: Full game state serialization to JSON, including room items, locked doors, flags, inventory, dropped items, and command history
- **Scoring system**: Multi-factor scoring with rank tiers from F to S
- **Narrative engine**: Typewriter-style text output with atmospheric descriptions and random ambient messages
- **Win condition**: Insert ID card + mysterious gem into the control room console to unlock the exit door

The entire game is self-contained in a single Python file with zero dependencies beyond the standard library.

## Running Tests

```bash
python3 -m pytest test_game.py -v
```

93 tests covering game initialization, item management, navigation, full puzzle walkthrough, save/load serialization, scoring/ranking, command parsing, hint system, and interactable data integrity.