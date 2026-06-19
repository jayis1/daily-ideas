# Nonogram (Picross) Puzzle Generator & Solver

A terminal-based Nonogram (Picross) puzzle game with automatic solving, puzzle generation, and interactive gameplay. Version 3.0.0.

## What It Does

- **Generates** random nonogram puzzles from procedural pixel-art patterns
- **Solves** any valid nonogram puzzle using constraint propagation + backtracking
- **Verifies** solution uniqueness for easy/medium difficulty puzzles
- **Counts** the number of solutions a puzzle has
- **Plays** interactively in the terminal with full keyboard controls
- **Exports/Imports** puzzles as compact JSON strings for sharing
- **Saves/Loads** game state so you can resume later
- **Times** your solve and tracks hints used and mistakes made

## Features

### Core
- Procedural puzzle generation with configurable size (3–20) and difficulty (easy, medium, hard)
- Automatic solver using constraint propagation + backtracking with timeout support
- Uniqueness verification ensures easy/medium puzzles always have exactly one solution
- Solution counting (`--count-solutions`) to diagnose non-unique puzzles

### Interactive Play
- Terminal UI with cursor, fill (Space/f), mark (x), clear (Backspace)
- Undo support (u), hints (h), auto-solve (S)
- Progress bar showing completion percentage
- Mistake counter and timer
- Row/column completion indicators (✓)
- Save game state (W) and export puzzle (e)

### CLI
- `--version` and `--help` flags
- `--generate` for non-interactive puzzle generation
- `--solve` to display the solution
- `--count-solutions` to enumerate solutions
- `--puzzle` and `--import-puzzle` for importing shared puzzles
- `--load` to resume a saved game
- `--seed` for reproducible puzzles
- `--no-color` for environments without ANSI support
- `-s` / `--size` and `-d` / `--difficulty` to configure the puzzle

### Bug Fix (v3.0.0)
The original `verify_unique_solution` function used a flawed cell-exclusion approach (`_solve_with_exclusion`) that could miss alternate solutions. It has been replaced with `count_solutions()` / `_find_all_solutions()` / `_search_solutions()` which correctly enumerates all solutions up to a given limit. Additionally, `generate_puzzle` no longer falls back to non-unique puzzles after 100 failed attempts — instead it derives subsequent seeds deterministically (`seed * 1000 + attempt`) and keeps trying until a unique puzzle is found.

## Installation

No external dependencies — uses only the Python standard library.

```bash
# Just run it directly
python3 nonogram.py

# Or make it executable
chmod +x nonogram.py
./nonogram.py --help
```

Requires Python 3.7+ (tested on 3.11+).

## Usage Examples

### Interactive Play
```bash
# Play a random 10×10 medium puzzle
python3 nonogram.py

# Play a 5×5 easy puzzle
python3 nonogram.py --size 5 --difficulty easy

# Play a 15×15 hard puzzle
python3 nonogram.py -s 15 -d hard

# Play a reproducible puzzle
python3 nonogram.py --seed 42
```

### Non-Interactive
```bash
# Generate and show solution
python3 nonogram.py --generate --solve --size 5 --seed 42

# Count solutions for a puzzle
python3 nonogram.py --generate --count-solutions --size 5 --seed 42

# Solve an imported puzzle
python3 nonogram.py --solve --puzzle '{"rows":5,"cols":5,"row_clues":[[3],[5],[5],[5],[3]],"col_clues":[[3],[5],[5],[5],[3]]}'

# Import and play a shared puzzle
python3 nonogram.py --import-puzzle '{"rows":5,"cols":5,"row_clues":[[3],[5],[5],[5],[3]],"col_clues":[[3],[5],[5],[5],[3]]}'
```

### Save & Resume
```bash
# Save: Press W during gameplay, then copy the JSON output
# Resume:
python3 nonogram.py --load '<saved-game-json>'
```

### Disable Colors
```bash
python3 nonogram.py --no-color
# Or set the NO_COLOR environment variable
NO_COLOR=1 python3 nonogram.py
```

## Controls (Interactive Mode)

| Key | Action |
|-----|--------|
| Arrow keys / WASD | Move cursor |
| Space / f | Fill cell |
| x | Mark cell (X) |
| Backspace | Clear cell |
| u | Undo |
| h | Hint (reveal one cell) |
| S | Auto-solve entire puzzle |
| e | Export puzzle as JSON |
| W | Save game state |
| q | Quit |

## Running Tests

```bash
python3 -m pytest test_nonogram.py -v
```

77 tests covering all core functionality including:
- Clue computation
- Line possibility generation
- Solver (constraint propagation + backtracking)
- Puzzle generation and solvability
- Solution checking
- Hint system
- Progress computation
- Export/import
- Pattern generation
- Uniqueness verification
- Solution counting
- Solver mismatch fix regression tests (seed=13)
- Save/load game state
- No-color flag

## Architecture

```
nonogram.py
├── ANSI Helpers (Style, cursor, screen)
├── Nonogram Logic
│   ├── compute_clues()          # Grid → row/col clues
│   ├── generate_line_possibilities()  # Clue → all valid line configs
│   ├── solve_nonogram()         # Constraint propagation + backtracking
│   ├── verify_unique_solution() # Check if puzzle has exactly one solution
│   ├── _find_all_solutions()    # Enumerate solutions up to a limit
│   ├── _search_solutions()      # Recursive search for solutions
│   ├── _propagate_for_search()  # Constraint propagation for search
│   ├── count_solutions()        # Public API for solution counting
│   ├── generate_puzzle()        # Generate random puzzle with uniqueness check
│   ├── generate_pattern()       # Generate random fill pattern
│   ├── check_solution()         # Verify player grid against solution
│   ├── get_hint()               # Find a cell to reveal
│   ├── export_puzzle()          # Puzzle → JSON string
│   ├── import_puzzle()          # JSON string → puzzle
│   ├── save_game_state()        # Game state → JSON string
│   ├── load_game_state()        # JSON string → game state
│   └── compute_progress()       # Calculate completion percentage
├── Terminal UI
│   └── NonogramGame             # Interactive game class
│       ├── draw()               # Render board
│       ├── play()               # Main game loop
│       ├── _save_and_show()     # Save and display JSON
│       └── _export_and_show()    # Export and display JSON
└── CLI (main)                   # argparse entry point
```

## License

MIT