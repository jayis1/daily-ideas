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
- **Flow visualization** — Press `f` to see which cells water reaches (highlighted in blue)
- **Auto-flow mode** — Press `a` to toggle live flow display that updates as you rotate
- **Undo support** — Press `u` to undo the last rotation (full undo stack)
- **Counter-clockwise rotation** — Press `R` (shift+r) to rotate counter-clockwise
- **Timer** — Tracks elapsed time; shows solve time on completion
- **Move counter** — Tracks total rotations made
- **Seed-based puzzles** — Use `--seed` for reproducible, shareable puzzles
- **Terminal size check** — Warns if terminal is too small for the grid
- **Configurable grid size** — Play on grids from 3×3 up to 15×20
- **`--version` and `--help`** — Standard CLI flags
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
python3 pipes_puzzle.py 10 15 3       # 10×15 Hard

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
4. Press `f` to **check flow** — cells that water reaches light up in blue
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
python3 -m pytest test_pipes_puzzle.py -v    # 42 tests with pytest
python3 test_pipes_puzzle.py                  # Direct run
```

Test coverage includes: pipe types, rotation logic, direction helpers, puzzle generation, flow checking, seed reproducibility, undo mechanics, grid dimension clamping, difficulty levels, and edge cases.

## What It Does

The game generates a random grid of pipe segments connected via a spanning tree, scrambles their rotations, and challenges you to rotate them back to form a continuous path from source to drain. It's a logic puzzle in the spirit of classic *Pipe Mania* / *PipeWorks*, rendered entirely in the terminal with Unicode box-drawing characters. Features include undo, live flow visualization, timer tracking, and seed-based reproducible puzzles for sharing challenges.