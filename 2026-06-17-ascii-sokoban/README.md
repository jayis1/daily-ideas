# ASCII Sokoban

A feature-rich terminal-based implementation of the classic **Sokoban** box-pushing puzzle game, rendered with beautiful Unicode box-drawing characters and colored ANSI output.

## What It Does

Sokoban (倉庫番, "warehouse keeper") is a puzzle game where you push boxes onto goal positions. The challenge: you can only **push** boxes, never pull them, and pushing a box into a corner can create an unsolvable deadlock!

## Features

- **8 progressively harder levels** — from a 2-box tutorial to multi-box challenges
- **Rich Unicode rendering** — walls (█), player (☺), boxes (■), goals (◇), boxes on goals (◆)
- **ASCII mode** — `--ascii` flag for terminals without Unicode support
- **ANSI color output** — colored walls, player, boxes, and goals for better visibility
- **`--no-color`** flag to disable colors if preferred
- **Full undo system** — press `u` to undo any move, as far back as you want
- **Deadlock detection** — warns when a box is stuck in a corner or against a wall with no reachable goal
- **Progress tracking** — shows boxes-on-goals counter (e.g., `2/4`) and elapsed time
- **Move & push counters** — track your efficiency
- **Level skip** — press `n` to skip to the next level
- **Level select** — start at any level with `-l` / `--level` flag
- **`--help` and `--version`** flags — standard CLI interface
- **Cross-session stats** — tracks total moves, pushes, and per-level bests

## Controls

| Key | Action |
|-----|--------|
| `↑` / `W` | Move up |
| `↓` / `S` | Move down |
| `←` / `A` | Move left |
| `→` / `D` | Move right |
| `U` | Undo last move |
| `R` | Restart level |
| `N` | Skip to next level |
| `Q` / `Ctrl+C` | Quit |

## Installation

No dependencies beyond Python 3.7+ and a terminal that supports ANSI escape codes (virtually all modern terminals).

```bash
# Just clone and run
git clone <repo-url>
cd ascii-sokoban
```

## How to Run

```bash
# Play from level 1 (default)
python3 sokoban.py

# Start at a specific level
python3 sokoban.py -l 3

# Use ASCII characters instead of Unicode
python3 sokoban.py --ascii

# Disable color output
python3 sokoban.py --no-color

# Show help
python3 sokoban.py --help

# Show version
python3 sokoban.py --version
```

## Usage Examples

### Starting the game
```bash
$ python3 sokoban.py
```

You'll see the first level rendered in your terminal with colored tiles:
```
  ╍━━━━━━━━╍
  Sokoban — Level 1/8  |  Moves: 0  Pushes: 0  Progress: 0/2  Time: 00:00
  ┏━━━━━━━━┓
  ┃  ████  ┃
  ┃  █  █  ┃
  ┃  █■ █  ┃
  ┃███  ███┃
  ┃█  ■ ◇█ ┃
  ┃█ ☺◇ ██ ┃
  ┃█████   ┃
  ┗━━━━━━━━┛

  Controls: ←↑↓→ / WASD move | u undo | r restart | n next | q quit
```

### Solving Level 1
Level 1 has 2 boxes and 2 goals. Push each box onto a diamond (◇) to win:
- Move up to position yourself left of a box
- Move right to push the box toward the goal
- Navigate around to push the second box
- Both boxes on goals = level complete!

### Deadlock Warning
If you push a box into a corner that isn't a goal, you'll see:
```
  ⚠ Deadlock detected! Press 'u' to undo or 'r' to restart.
```

### Completing a Level
```
  ★ Congratulations! Level complete in 10 moves, 3 pushes, 00:42!
  Press any key to continue...
```

### ASCII Mode
For terminals that don't support Unicode well:
```bash
$ python3 sokoban.py --ascii
```
Uses `#` for walls, `@` for player, `$` for boxes, `.` for goals, `*` for boxes on goals.

## Game Rules

1. You are the player (☺). Move in four directions.
2. When you move into a box (■), you **push** it one cell in that direction.
3. You cannot push a box into a wall or another box.
4. You cannot pull boxes — only push.
5. Place all boxes onto goal positions (◇) to complete the level.
6. A box on a goal shows as (◆).

## Levels

| Level | Boxes | Difficulty | Description |
|-------|-------|------------|-------------|
| 1 | 2 | ★☆☆☆☆ | Tutorial — learn the basics |
| 2 | 2 | ★★☆☆☆ | Two boxes, tighter space |
| 3 | 2 | ★★★☆☆ | L-shaped maze |
| 4 | 2 | ★★★☆☆ | Tight corridors with central obstacle |
| 5 | 4 | ★★★★☆ | Four boxes, multiple goals |
| 6 | 3 | ★★★☆☆ | Zigzag paths |
| 7 | 4 | ★★★★☆ | Open layout with four boxes |
| 8 | 3 | ★★★★☆ | Narrow passages — the gauntlet |

## Running Tests

```bash
cd ascii-sokoban
python3 -m pytest test_sokoban.py -v
```

Tests cover: level parsing, movement logic, win detection, deadlock detection, rendering (Unicode & ASCII modes), stats tracking, and level integrity (all levels parse correctly with matching box/goal counts).

## Technical Details

- **Rendering**: ANSI/VT100 escape codes for cursor positioning, screen clearing, and cursor hiding. Optional color output with distinct colors for walls, player, boxes, and goals.
- **Input**: Raw terminal mode (`tty.setraw`) for single-keypress reading without Enter.
- **Undo**: Full state history stored as `(state, moves, pushes)` tuples — undo restores exact counters, not just board position.
- **Deadlock detection**: Corner deadlock heuristic (box wedged between two perpendicular walls) and wall-line deadlock detection (box against a wall with no reachable goal along that line).
- **CLI**: `argparse`-based interface with `--help`, `--version`, `--level`, `--ascii`, and `--no-color` flags.
- **Version**: 1.1.0

## License

MIT