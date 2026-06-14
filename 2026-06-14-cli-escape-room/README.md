# 🚪 CLI Escape Room

**v1.0.0** — A fully interactive text-based escape room game for your terminal. Wake up in a locked cell with no memory. Explore rooms, collect items, solve interconnected puzzles, and escape a mysterious underground facility.

## Description

You wake up in a concrete cell. No idea how you got here. The door is locked. A faint hum echoes through the walls. Somewhere beyond these walls lies freedom — but only if you can solve the puzzles that stand between you and the exit.

**CLI Escape Room** is a richly detailed text adventure with 6 interconnected rooms, 12 collectible items, and multiple puzzle chains that must be solved in sequence. Every item has a purpose, every clue connects to something, and the story of *Project Mnemosyne* unfolds as you explore.

## Features

- **6 rooms**: Cell, Corridor, Study, Laboratory, Hidden Passage, Control Room
- **12 items**: Keys, wires, notes, tools, a flashlight, a mysterious gem, and more
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
- **Move counter and timer** tracking your escape attempt
- **Command parser** with aliases and fuzzy matching
- **ASCII art** title screen and victory screen

## Installation

No dependencies required — uses only Python 3 standard library.

```bash
# Clone or download
cd ~/daily-ideas/2026-06-14-cli-escape-room
```

## How to Run

```bash
python3 escape_room.py
```

## Usage

### Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `look [thing]` | `l`, `examine`, `inspect`, `check` | Look around or examine something specific |
| `go <direction>` | `move`, `walk`, `enter` | Move to another room (north/south/east/west) |
| `take <item>` | `get`, `grab`, `pick up` | Pick up an item |
| `use <item> on <thing>` | `apply`, `insert`, `connect` | Use an item on something |
| `combine <things>` | `join`, `merge` | Combine items (e.g., note fragments) |
| `inventory` | `i`, `inv`, `items` | Show your inventory |
| `help` | `h`, `?` | Show command help |
| `quit` | `exit`, `q` | Quit the game |

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

▸ What do you do? go north
You head north...
[Corridor description]

▸ What do you do? look at clock
The clock is ornate, with carved mahogany. The face reads 3:33.
You notice '3333' etched into the back panel...
You take: Old Photograph

▸ What do you do? keypad
The keypad display blinks, waiting for a 4-digit code.
    ▸ Enter 4-digit code: 3333
✓ ACCESS GRANTED!
```

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

- **Game engine**: Room navigation, inventory management, puzzle state tracking via flags, locked door system
- **Parser**: Natural-ish command processing with aliases and fuzzy direction matching
- **Puzzle system**: Multiple puzzle types — key locks, combination locks, code keypads, item-on-object interactions, item combination, dark room mechanics
- **Narrative engine**: Typewriter-style text output with atmospheric descriptions
- **Win condition**: Insert ID card + mysterious gem into the control room console to unlock the exit door

The entire game is self-contained in a single ~450-line Python file with zero dependencies beyond the standard library.