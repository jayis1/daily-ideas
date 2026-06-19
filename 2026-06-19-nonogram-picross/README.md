# Nonogram (Picross) Puzzle Generator & Solver

A terminal-based Nonogram (also known as Picross) puzzle game with procedural generation, an automatic solver using constraint propagation + backtracking, solution uniqueness verification, and interactive gameplay with keyboard controls, undo support, and progress tracking.

## What is Nonogram?

Nonogram is a logic puzzle where you fill cells in a grid based on numerical clues. Each row and column has a set of numbers indicating the lengths of consecutive filled blocks. For example, a clue of `3 1` means there's a block of 3 filled cells, then at least one gap, then a block of 1 filled cell. The challenge is to figure out which cells are filled and which are empty.

## Features

- **Procedural Generation** — Creates random puzzles with three difficulty levels:
  - **Easy** (5×5): Simple shapes and high fill ratio
  - **Medium** (10×10): Symmetric patterns with moderate complexity
  - **Hard** (15×15): Dense clustered patterns
- **Solution Uniqueness Verification** — Easy and medium puzzles are verified to have exactly one solution
- **Automatic Solver** — Uses constraint propagation to deduce cells, with backtracking for remaining unknowns and a configurable timeout
- **Interactive Gameplay** — Full terminal UI with keyboard controls:
  - Arrow keys / WASD to move the cursor
  - Space/F to fill a cell
  - X to mark a cell as definitely empty (✕)
  - Backspace to clear a cell
  - U to undo the last action
  - H for a hint (reveals one cell)
  - S to auto-solve the entire puzzle
  - E to export/share the puzzle
  - Q to quit
- **Undo Support** — Press U to undo any action (fill, mark, clear, hint), with a capped history buffer
- **Progress Bar** — Real-time visual progress indicator showing completion percentage
- **Visual Feedback** — Completed rows/columns light up in green with a ✓ indicator
- **Timer & Stats** — Tracks time, hints used, and mistakes made
- **Seed-Based Reproducibility** — Use `--seed N` to generate the same puzzle every time
- **Puzzle Export/Import** — Share puzzles as compact JSON strings; import and play shared puzzles interactively
- **Input Validation** — Robust error handling for invalid puzzle imports, dimension mismatches, and oversized puzzles
- **`--version` and `--help` Flags** — Standard CLI flags included

## How to Install

No external dependencies required! Uses only Python standard library modules.

```bash
# Clone or download the script
cp nonogram.py /usr/local/bin/nonogram  # optional: install system-wide
chmod +x nonogram.py
```

Requires Python 3.7+ (uses f-strings, `dataclasses`-style patterns, and `termios` for interactive mode).

## How to Run

### Interactive Game

```bash
# Play a random 10×10 medium puzzle
python3 nonogram.py

# Play a 5×5 easy puzzle
python3 nonogram.py --size 5 --difficulty easy

# Play a 15×15 hard puzzle
python3 nonogram.py --size 15 --difficulty hard

# Play a reproducible puzzle (same seed = same puzzle)
python3 nonogram.py --seed 42

# Check version
python3 nonogram.py --version

# See all options
python3 nonogram.py --help
```

### Generate & Display Puzzles

```bash
# Generate a 10×10 puzzle and display it
python3 nonogram.py --generate

# Generate and show the solution
python3 nonogram.py --generate --solve

# Generate a 5×5 easy puzzle with solution
python3 nonogram.py --generate --size 5 --difficulty easy --solve

# Generate with a specific seed for reproducibility
python3 nonogram.py --generate --seed 42 --solve
```

### Solve Imported Puzzles

```bash
# Solve a puzzle from a JSON string
python3 nonogram.py --puzzle '{"rows": 5, "cols": 5, "row_clues": [[1, 2], [2], [2], [2], [1]], "col_clues": [[0], [1], [1], [4], [4]]}' --solve

# Display an imported puzzle without solving
python3 nonogram.py --puzzle '{"rows": 5, "cols": 5, "row_clues": [[1, 2], [2], [2], [2], [1]], "col_clues": [[0], [1], [1], [4], [4]]}'
```

### Import & Play Shared Puzzles

```bash
# Import a puzzle and play it interactively
python3 nonogram.py --import-puzzle '{"rows": 5, "cols": 5, "row_clues": [[3, 1], [4], [3], [1, 1], [1, 1]], "col_clues": [[4], [3], [5], [1], [1, 1]]}'
```

## Usage Examples

### Solving Strategy

1. Start with rows/columns that have large clue numbers — they have fewer possibilities
2. Look for clues that sum close to the grid size — these constrain heavily
3. Use X marks (press X) to note cells you know are empty
4. Press U to undo mistakes
5. Use H for hints when stuck
6. Watch for green ✓ indicators showing completed rows/columns

### Example Output (5×5 Easy, Seed 42)

```
  ◇ NONOGRAM PICROSS ◇  (5×5)

          4  3  5  1  1
                      1
        ────────────────
  3  1 │· · · · · 
     4 │· · · · · 
     3 │· · · · · 
  1  1 │· · · · · 
  1  1 │· · · · · 
```

### Solved Output

```
  ◇ NONOGRAM PICROSS ◇  (5×5)

          4  3  5  1  1
                      1
        ────────────────
  3  1 │█ █ █ · █ 
     4 │█ █ █ █ · 
     3 │█ █ █ · · 
  1  1 │█ · █ · · 
  1  1 │· · █ · █ 
```

## How It Works

### Constraint Propagation Solver

The solver generates all valid line configurations for each row and column based on their clues. It then iteratively:

1. **Filters possibilities** — Eliminates configurations that conflict with known cells
2. **Fixes known cells** — If all remaining possibilities agree on a cell's value, that cell is determined
3. **Repeats** until no more cells can be determined

If cells remain unknown after propagation, **backtracking** is used — trying each possibility for an unknown cell and recursively solving.

### Solution Uniqueness Verification

For easy and medium puzzles, the generator verifies that each puzzle has exactly one valid solution. It finds the first solution, then tries to find a second by forcing cells to differ. This ensures the puzzle is solvable purely through logic.

### Pattern Generation

Puzzles are generated by creating random pixel-art patterns:

- **Easy**: Simple rectangles and shapes with random fill
- **Medium**: Horizontally/vertically symmetric patterns
- **Hard**: Dense clustered patterns using neighbor propagation

Clues are then computed from the generated pattern.

### Undo System

Every cell change (fill, mark, clear, hint) is pushed onto an undo stack (capped at 1000 entries, trimmed to 500 when exceeded). Pressing U pops the last action and restores the previous cell state.

## File Structure

```
nonogram.py          # Main game script (generator, solver, interactive UI)
test_nonogram.py     # Test suite (63 tests)
README.md            # This file
```

## Running Tests

```bash
python3 -m pytest test_nonogram.py -v
```

All 63 tests cover: clue computation, line possibility generation (including infeasible clues), solver correctness (including timeout and single-cell), puzzle generation with seeds, solution checking (including X-mark semantics), hint system, progress tracking, export/import roundtrip with validation, uniqueness verification, pattern generation, and version format.

## Version

**2.0.0** — Added undo support, seed-based reproducibility, progress bar, solution uniqueness verification, `--version`/`--import-puzzle` flags, input validation, solver timeout, improved error handling, and 31 new tests (up from 32 to 63).