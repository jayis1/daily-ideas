# Nonogram Picross

A terminal-based Nonogram (Picross) puzzle game and solver written in Python.

## Features

- **Interactive gameplay** — Play nonogram puzzles in your terminal with keyboard controls
- **Automatic solver** — Constraint-propagation solver that can solve puzzles instantly
- **Puzzle generation** — Generate random puzzles at three difficulty levels (easy, medium, hard)
- **Unique solution guarantee** — Easy and medium puzzles are verified to have exactly one solution
- **Solution counter** — Count the number of solutions a puzzle has
- **Save/Load** — Save and resume game state via JSON
- **Undo support** — Full undo history during gameplay
- **Hints** — Get hints when stuck
- **Progress tracking** — See completion percentage in real time
- **No-color mode** — `--no-color` flag or `NO_COLOR` env var for ANSI-free output
- **Seed-based reproducibility** — Use `--seed` for deterministic puzzle generation

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd 2026-06-19-nonogram-picross

# No external dependencies required — uses only Python standard library
# Just run it directly:
python3 nonogram.py --help
```

## Usage

### Play an interactive game

```bash
# Random medium puzzle
python3 nonogram.py

# Easy 5×5 puzzle with a specific seed
python3 nonogram.py --size 5 --difficulty easy --seed 42

# No color output
python3 nonogram.py --no-color
```

### Generate and solve puzzles

```bash
# Generate and show the solution
python3 nonogram.py --generate --solve --size 10 --seed 42

# Generate and count solutions
python3 nonogram.py --generate --count-solutions --size 10 --seed 42

# Solve a puzzle from JSON
python3 nonogram.py --solve --puzzle '{"rows":5,"cols":5,"row_clues":[[3],[5],[5],[5],[3]],"col_clues":[[3],[5],[5],[5],[3]]}'
```

### Save and load games

```bash
# During gameplay, press W to save state to a JSON file
# Load a saved game:
python3 nonogram.py --load saved_game.json
```

### All CLI flags

| Flag | Description |
|------|-------------|
| `--help` | Show help message and exit |
| `--version` | Show version and exit |
| `--size N` | Puzzle size (default: 10) |
| `--difficulty LEVEL` | `easy`, `medium`, or `hard` (default: `medium`) |
| `--seed N` | Random seed for reproducibility |
| `--generate` | Generate a new puzzle |
| `--solve` | Solve the puzzle automatically |
| `--count-solutions` | Count all solutions for the puzzle |
| `--puzzle JSON` | Import puzzle from JSON string |
| `--load FILE` | Load a saved game from file |
| `--no-color` | Disable ANSI color/escape codes |

### In-game controls

| Key | Action |
|-----|--------|
| Arrow keys / hjkl | Move cursor |
| Space / Enter | Fill cell |
| X / Backspace | Mark empty |
| Z | Undo |
| H | Hint |
| P | Show progress |
| W | Save game state |
| Q | Quit |

## Architecture

```
nonogram.py
├── Display & ANSI utilities
│   ├── Style (metaclass-based, respects --no-color)
│   ├── clear_screen, move_cursor, hide_cursor, show_cursor
│   └── draw_grid, draw_progress_bar, draw_hint_animation
├── Nonogram Logic
│   ├── compute_clues, compute_line_possibilities
│   ├── solve_nonogram (constraint propagation + backtracking)
│   ├── count_solutions, _find_all_solutions
│   ├── generate_pattern, generate_puzzle
│   └── check_solution, compute_progress
├── Game State
│   ├── NonogramGame class
│   └── save_game_state, load_game_state
└── CLI entry point (argparse)
```

## Testing

```bash
python3 -m pytest test_nonogram.py -v
```

The test suite includes 96 tests covering:
- Clue computation and solver correctness
- Puzzle generation and uniqueness verification
- Solution counting
- Save/load round-trip
- Input validation (dimension bounds, difficulty strings, cursor bounds)
- No-color mode behavior
- Edge cases (zero dimensions, None values, dimension mismatches)

## Bug Fixes (v3.1.0)

- **`--no-color` flag** — Previously had no effect (global `_NO_COLOR` was never set by CLI). Now uses a `_StyleMeta` metaclass that dynamically returns empty ANSI strings when `_NO_COLOR` is True, and properly sets the flag from both `--no-color` and the `NO_COLOR` environment variable
- **`check_solution` with None values** — `None` in player_grid cells was compared with `-1`/`1`/`0` using `==`, which could incorrectly match. Now explicitly checks for `None` values
- **`compute_progress` IndexError on dimension mismatch** — If `player_grid` and `solution` had different dimensions, the function would crash. Now returns `0.0` gracefully
- **`load_game_state` missing validation** — Didn't validate `player_grid` dimensions or cursor bounds. Now raises `ValueError` on corrupted/mismatched data
- **`NonogramGame(size=0)` ZeroDivisionError** — Size 0 caused division-by-zero errors. Now validates `size >= 2`
- **`generate_puzzle` invalid difficulty** — Invalid difficulty strings silently fell through to "hard". Now raises `ValueError`
- **`generate_pattern(0, 0)` ValueError** — Zero-dimension patterns caused errors. Now validates dimensions and handles 1-row/1-column edge cases
- **Terminal escape sequences in no-color mode** — `clear_screen`, `move_cursor`, `hide_cursor`, and `show_cursor` now skip ANSI output when `_NO_COLOR` is set

## Changelog

- **v3.1.0** — Bug fix release: input validation, no-color mode fix, edge case handling
- **v3.0.0** — Solver mismatch fix, save/load, solution counter, no-color flag (incomplete)
- **v2.1.0** — Initial enhanced version

## License

MIT