# 🧩 Pipes Puzzle

A terminal-based pipe rotation puzzle game built with Python and `curses`. Rotate pipe segments on a grid to connect water flow from the source (▶ left side) to the drain (▶ right side).

```
  ▶ ═ ╝ ╞ ╝ ╥ ╗ ╝ ▶
    ╞ ╠ ╥ ╣ ╬ ╦ ╠
    ╞ ╠ ╣ ╠ ╔ ═ ╬
    ╗ ╦ ╠ ╣ ╝ ╥ ║
    ╔ ═ ╦ ╦ ╚ ╔ ╚
```

## Features

- **Procedural generation** — Every puzzle is unique, built via randomized Kruskal's spanning tree
- **Three difficulty levels** — Easy (scrambled ≠ correct), Medium (extra loops/tees), Hard (more loops + random scramble)
- **Flow visualization** — Press `f` or `Enter` to see which cells water reaches (highlighted in blue)
- **Auto-flow mode** — Press `a` to toggle live flow display that updates as you rotate
- **Undo support** — Press `u` to undo the last rotation (full undo stack)
- **Counter-clockwise rotation** — Press `R` (shift+r) to rotate counter-clockwise
- **Timer** — Tracks elapsed time; shows solve time on completion
- **Move counter** — Tracks total rotations made
- **Seed-based puzzles** — Use `--seed` for reproducible, shareable puzzles
- **Terminal size check** — Warns if terminal is too small for the grid
- **Configurable grid size** — Play on grids from 3×3 up to 15×20
- **`--version` and `--help`** — Standard CLI flags
- **Time-based message display** — Messages auto-dismiss after a few seconds (not tied to keypresses)
- **Cursor movement after solving** — You can still examine the puzzle after solving it
- **Cross-platform Enter key** — Supports LF (10), CR (13), and curses.KEY_ENTER for flow check
- **Fully terminal-based** — No external dependencies, just Python 3.7+ with curses

## Installation

No external packages needed — just Python 3.7+ with the standard library:

```bash
chmod +x pipes_puzzle.py
```

## How to Run

```bash
# Default: 7×9 grid, Medium difficulty
python3 pipes_puzzle.py

# Custom size: rows cols [difficulty]
python3 pipes_puzzle.py 5 7 1        # 5×7 Easy
python3 pipes_puzzle.py 10 15 3      # 10×15 Hard

# Reproducible puzzle with a seed
python3 pipes_puzzle.py --seed 42

# Auto-flow mode (live water visualization)
python3 pipes_puzzle.py --auto-flow

# Combined
python3 pipes_puzzle.py 8 10 2 --seed 1234 --auto-flow

# Show version
python3 pipes_puzzle.py --version

# Show help
python3 pipes_puzzle.py --help
```

## Controls

| Key | Action |
|-----|--------|
| `↑` / `k` | Move cursor up |
| `↓` / `j` | Move cursor down |
| `←` / `h` | Move cursor left |
| `→` / `l` | Move cursor right |
| `r` / `Space` | Rotate pipe clockwise |
| `R` (shift+r) | Rotate pipe counter-clockwise |
| `u` | Undo last rotation |
| `f` / `Enter` | Check flow (show water reach) |
| `a` | Toggle auto-flow mode |
| `n` | New puzzle |
| `q` / `Esc` | Quit |

## How to Play

1. A **▶** on the left marks the **source** (water entry point)
2. A **▶** on the right marks the **drain** (water exit point)
3. **Rotate** each pipe segment by moving the cursor over it and pressing `r` or `Space`
4. Press `f` or `Enter` to **check flow** — cells that water reaches light up in blue
5. Press `a` to **toggle auto-flow** — water flow updates live as you rotate
6. Press `u` to **undo** a rotation mistake
7. When water flows from source all the way to drain, you **win!** 🎉

## Pipe Types

| Symbol | Type | Connections |
|--------|------|-------------|
| ║ ═ | Straight | Opposite sides (top-bottom or left-right) |
| ╔ ╗ ╝ ╚ | Elbow | Adjacent sides (corner connections) |
| ╩ ╠ ╦ ╣ | Tee | Three sides |
| ╬ | Cross | All four sides |
| ╨ ╞ ╥ ╡ | Dead End | One side only |

## Difficulty Levels

| Level | Description |
|-------|-------------|
| 1 (Easy) | Scrambled pipes guaranteed ≠ solved state; fewer loops |
| 2 (Medium) | Extra edges create loops with tees and crosses; random scramble |
| 3 (Hard) | Even more loops; random scramble may occasionally pre-solve |

## Algorithm Details

- **Generation**: Kruskal's algorithm with random edge ordering creates a spanning tree of the grid, guaranteeing every cell is reachable. External connections (LEFT on source row's first cell, RIGHT on drain row's last cell) are forced.
- **Difficulty 2+**: Extra non-tree edges are added to create loops, resulting in more T-junctions and cross pieces.
- **Pipe assignment**: Each cell's pipe type is determined by its number of connections (2=straight/elbow, 3=tee, 4=cross, 1=dead end) and orientation.
- **Flow checking**: BFS from source following mutual pipe connections; solved when water reaches the drain row's rightmost cell with a RIGHT-facing connection.

## Testing

```bash
python3 -m pytest test_pipes_puzzle.py -v    # 48 tests with pytest
python3 test_pipes_puzzle.py                  # Direct run
```

Test coverage includes: pipe types, rotation logic, direction helpers, puzzle generation, flow checking, seed reproducibility, undo mechanics, grid dimension clamping, difficulty levels, edge cases, and bug fix regressions (rotated char mapping, Enter key handling, message timing).

## Changelog

### v2.1.0 — Bug fixes

- **Fixed `PipeType.rotated()` character mapping** — The `rotated()` method computed character positions using `chars[(i - times) % 4]` instead of the correct `chars[(i + times) % 4]`, causing rotation 1 and 3 characters to be swapped for ELBOW, TEE, and DEAD_END pipe types. While this method wasn't called by the game itself (which uses `pipe_char(ptype, rotation)` directly), the API was incorrect.
- **Fixed Enter key for flow check** — The flow check only recognized key code 10 (LF/Unix Enter). Now also recognizes key code 13 (CR/Windows Enter) and `curses.KEY_ENTER`, ensuring Enter works for flow checking across all terminal types.
- **Fixed cursor movement after solving** — After solving the puzzle, all keys except `n` (new) and `q` (quit) were blocked, including cursor movement. Now movement keys (`hjkl`, arrow keys), undo (`u`), and auto-flow toggle (`a`) work after solving, so you can examine the solution.
- **Fixed message display timing** — Messages previously used a keypress-counter (`message_timer`) that decremented once per draw call, making message duration depend on how fast the user pressed keys. Now uses real-time expiry (`message_expiry`), so messages consistently display for their intended duration (2–5 seconds) regardless of keypress speed.
- **Fixed undo feedback when solved** — Pressing `u` after solving previously did nothing silently. Now displays "Already solved! Press 'n' for new puzzle." for 3 seconds.
- **Added 6 regression tests** — Tests for `PipeType.rotated()` char and connection mapping, Enter key codes, message timing, and version bump verification.