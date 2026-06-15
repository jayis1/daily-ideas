# 🧩 Pipes Puzzle

A terminal-based pipe rotation puzzle game built with Python and `curses`. Rotate pipe segments on a grid to connect water flow from the source (▶ left side) to the drain (▶ right side).

```
  ▶ ═ ╝ ╞ ╝ ╥ ╗ ╝ ▶
    ╞ ╠ ╥ ╣ ╬ ╦ ╠
    ╞ ╠ ╣ ╠ ╔ ═ ╬
    ╗ ╦ ╠ ╣ ╝ ╥ ║
    ╔ ═ ╦ ╦ ╚ ╔ ╚
```

## How It Works

A random puzzle is generated using a spanning tree algorithm that guarantees a valid solution exists. Pipe segments are then randomly rotated, and your goal is to rotate them back to restore the water path from source to drain.

### Pipe Types

| Symbol | Type | Connections |
|--------|------|-------------|
| ║ ═ | Straight | Opposite sides (top-bottom or left-right) |
| ╔ ╗ ╝ ╚ | Elbow | Adjacent sides (corner connections) |
| ╩ ╠ ╦ ╣ | Tee | Three sides |
| ╬ | Cross | All four sides |
| ╨ ╞ ╥ ╡ | Dead End | One side only |

## Features

- **Procedural generation** — Every puzzle is unique, built via randomized Kruskal's spanning tree
- **Three difficulty levels** — Easy (scrambled ≠ correct), Medium (extra loops/tees), Hard (more loops + random scramble)
- **Flow visualization** — Press `f` to see which cells water currently reaches (highlighted in blue)
- **Move counter** — Track how many rotations you've made
- **Fully terminal-based** — No external dependencies, just Python + curses
- **Configurable grid size** — Play on grids from 3×3 up to 15×20

## Installation

No external packages needed — just Python 3.7+ with standard library:

```bash
# Clone or download the script
chmod +x pipes_puzzle.py
```

## How to Run

```bash
# Default: 7×9 grid, difficulty 2
python3 pipes_puzzle.py

# Custom size: rows cols [difficulty]
python3 pipes_puzzle.py 5 7 1     # 5×7 easy
python3 pipes_puzzle.py 10 15 3   # 10×15 hard
```

## Controls

| Key | Action |
|-----|--------|
| `↑` / `k` | Move cursor up |
| `↓` / `j` | Move cursor down |
| `←` / `h` | Move cursor left |
| `→` / `l` | Move cursor right |
| `r` / `Space` | Rotate pipe clockwise |
| `f` / `Enter` | Check flow (show water reach) |
| `n` | New puzzle |
| `q` / `Esc` | Quit |

## How to Play

1. A **▶** on the left marks the **source** (water entry point)
2. A **▶** on the right marks the **drain** (water exit point)
3. **Rotate** each pipe segment by moving the cursor over it and pressing `r` or `Space`
4. Press `f` to **check flow** — cells that water reaches light up in blue
5. When water flows from source all the way to drain, you **win!** 🎉

## Algorithm Details

- **Generation**: Kruskal's algorithm with random edge ordering creates a spanning tree of the grid. This guarantees every cell is reachable. External connections (LEFT on source row's first cell, RIGHT on drain row's last cell) are forced.
- **Difficulty 2+**: Extra non-tree edges are added to create loops, resulting in more T-junctions and cross pieces.
- **Pipe assignment**: Each cell's pipe type is determined by its number of connections (2=straight/elbow, 3=tee, 4=cross, 1=dead end) and orientation.

## Testing

```bash
python3 test_pipes_puzzle.py     # Unit tests
python3 integration_test.py      # Integration tests (full solve verification)
```

## What It Does

The game generates a random grid of pipe segments connected via a spanning tree, scrambles their rotations, and challenges you to rotate them back to form a continuous path from source to drain. It's a logic puzzle in the spirit of classic *Pipe Mania* / *PipeWorks*, rendered entirely in the terminal with Unicode box-drawing characters.