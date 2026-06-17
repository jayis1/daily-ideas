# ASCII Sokoban

A terminal-based implementation of the classic **Sokoban** box-pushing puzzle game, rendered with beautiful Unicode box-drawing characters and tile symbols.

## What It Does

Sokoban (倉庫番, "warehouse keeper") is a puzzle game where you push boxes onto goal positions. The challenge: you can only **push** boxes, never pull them, and pushing a box into a corner can create an unsolvable deadlock!

This implementation features:
- **5 progressively harder levels** — from a 2-box tutorial to a 4-box challenge
- **Rich Unicode rendering** — walls (█), player (☺), boxes (■), goals (◇), boxes on goals (◆)
- **Full undo system** — press `u` to undo any move, as far back as you want
- **Deadlock detection** — warns when a box is stuck in a corner that's not a goal
- **Move & push counters** — track your efficiency
- **Timer** — how fast can you clear each level?
- **Arrow key + WASD support** — move with whatever feels natural
- **Instant restart** — press `r` to reset the current level

## Controls

| Key | Action |
|-----|--------|
| `↑` / `W` | Move up |
| `↓` / `S` | Move down |
| `←` / `A` | Move left |
| `→` / `D` | Move right |
| `U` | Undo last move |
| `R` | Restart level |
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
python3 sokoban.py
```

## Usage Examples

### Starting the game
```bash
$ python3 sokoban.py
```

You'll see the first level rendered in your terminal:
```
  ╍━━━━━━━━╍
  Sokoban — Level 1/5  |  Moves: 0  Pushes: 0  Time: 00:00
  ┏━━━━━━━━┓
  ┃  ████  ┃
  ┃  █  █  ┃
  ┃  █■ █  ┃
  ┃███  ███┃
  ┃█  ■ ◇█ ┃
  ┃█ ☺◇ ██ ┃
  ┃█████   ┃
  ┗━━━━━━━━┛

  Controls: ←↑↓→ / WASD move │ u undo │ r restart │ q quit
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

## Technical Details

- **Rendering**: ANSI/VT100 escape codes for cursor positioning, screen clearing, and cursor hiding
- **Input**: Raw terminal mode (`tty.setraw`) for single-keypress reading without Enter
- **Undo**: Full state history with `copy.deepcopy` — undo back to the very first move
- **Deadlock detection**: Simple corner deadlock heuristic — checks if a box is wedged between two perpendicular walls

## License

MIT