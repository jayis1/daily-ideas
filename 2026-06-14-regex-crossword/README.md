# Regex Crossword Generator & Solver

**v1.1.0** — A CLI tool for generating and solving **regex crossword puzzles** — a mind-bending puzzle type where each cell must satisfy both a row regex constraint and a column regex constraint simultaneously. Think of it as a cross between Sudoku and regular expressions!

## What is a Regex Crossword?

In a regex crossword, you fill a grid with characters where:

- Each **row** must match its corresponding regex pattern
- Each **column** must match its corresponding regex pattern
- Every cell sits at the intersection of a row and column, so it must satisfy **both** constraints

Example (2×2 tutorial puzzle):

```
        C1       C2
   ┌─────────┬─────────┐
R1 │  A  │  B  │   ← matches /A./
   ├─────────┼─────────┤
R2 │  C  │  1  │   ← matches /.1/
   └─────────┴─────────┘
      ↑        ↑
   /A./     /.1/
```

- Row 1 `AB` matches `/A./` ✓
- Row 2 `C1` matches `/.1/` ✓
- Column 1 `AC` matches `/A./` ✓
- Column 2 `B1` matches `/.1/` ✓

## Features

### Core Puzzles & Solving
- **6 built-in puzzles** of varying difficulty (tutorial → alpha_chaos)
- **Random puzzle generation** with configurable grid size (2×2 to 8×8)
- **3 difficulty levels** controlling regex complexity (simple literals → alternations → quantifiers)
- **6 character sets**: hex, alpha, digits, vowels, alphanumeric, binary
- **Backtracking solver** with full-row/full-column constraint pruning
- **Brute force solver** for verification on small puzzles
- **Solution validator** that checks all regex constraints with detailed error reporting

### Interactive Play
- **Interactive terminal UI** with:
  - Arrow key navigation and auto-advance after typing
  - Real-time constraint validation with color-coded cells:
    - 🟢 Green = both row and column constraints satisfied
    - 🟡 Yellow = row constraint only
    - 🟣 Purple = column constraint only
    - 🔴 Red = neither constraint met
  - Row/column pattern status indicators (✓/✗)
  - **Hint system** — reveal a single cell
  - **Auto-solve** — reveal the entire solution
  - **Reset** — clear all cells and start over

### New in v1.1.0
- **Timer mode** (`--timer`) — tracks elapsed time while playing
- **Move counter** — tracks how many cells you've filled
- **Hint counter** — tracks how many hints/auto-solves you've used
- **Game statistics** — on completion, shows moves, hints, and time
- **JSON export** (`--export`) — export any puzzle as JSON for sharing
- **JSON import** (`--import`) — import and play puzzles from JSON files
- **Solution uniqueness checker** (`--unique`) — verify if a puzzle has a unique solution
- **Solution counter** (`count_solutions()`) — count the number of valid solutions (up to a limit)
- **`--version` flag** — display version number
- **2 new built-in puzzles**: `binary_blitz` (3×3, binary charset) and `alpha_chaos` (4×4, letter ranges)
- **Binary charset** — puzzles using only `0` and `1`
- **Robust error handling** — graceful handling of invalid regex patterns, bad JSON, missing fields
- **Extended grid size** — now supports up to 8×8
- **Named puzzles** — each puzzle carries its name for display and serialization

## Installation

No external dependencies needed — uses only Python standard library (3.7+).

```bash
# Clone or download the project
cd regex-crossword

# Run directly
python3 regex_crossword.py --help
python3 regex_crossword.py --version
```

## Usage

### Play a built-in puzzle interactively

```bash
python3 regex_crossword.py --play tutorial
python3 regex_crossword.py --play easy
python3 regex_crossword.py --play medium
python3 regex_crossword.py --play vowel_vortex
python3 regex_crossword.py --play binary_blitz
python3 regex_crossword.py --play alpha_chaos
```

### Play with a timer

```bash
python3 regex_crossword.py --timer --play medium
```

### Generate a random puzzle

```bash
# 3×3 grid, easy difficulty, hex charset
python3 regex_crossword.py --generate 3 3

# 4×4 grid, medium difficulty, alpha charset  
python3 regex_crossword.py --generate 4 4 --diff 2 --charset alpha

# 5×5 grid, hard difficulty, digits only
python3 regex_crossword.py --generate 5 5 --diff 3 --charset digit --verify

# Generate and check solution uniqueness
python3 regex_crossword.py --generate 3 3 --unique
```

### Print a puzzle in text mode

```bash
python3 regex_crossword.py --print tutorial
python3 regex_crossword.py --print binary_blitz
```

### Solve a puzzle and show the answer

```bash
python3 regex_crossword.py --solve tutorial
python3 regex_crossword.py --solve medium
python3 regex_crossword.py --solve medium --unique
```

### Export and import puzzles as JSON

```bash
# Export a puzzle to stdout
python3 regex_crossword.py --export easy > my_puzzle.json

# Import and play a JSON puzzle
python3 regex_crossword.py --import my_puzzle.json

# Import with verification
python3 regex_crossword.py --import my_puzzle.json --verify --timer
```

### List available puzzles

```bash
python3 regex_crossword.py --list
```

### Check all predefined puzzles for uniqueness

```bash
python3 regex_crossword.py --unique
```

### Display version

```bash
python3 regex_crossword.py --version
```

## Interactive Controls

| Key | Action |
|-----|--------|
| Arrow keys | Move cursor |
| A-Z, 0-9 | Fill cell with character |
| Delete/Backspace | Clear cell |
| Tab | Move to next cell |
| H | Hint (reveal current cell) |
| S | Solve (reveal entire solution) |
| R | Reset (clear all cells + reset stats) |
| Q | Quit |

## Built-in Puzzles

| Name | Size | Description |
|------|------|-------------|
| `tutorial` | 2×2 | Simple dot-matching patterns |
| `easy` | 3×3 | Literal row/column strings |
| `medium` | 3×3 | Character classes and quantifiers |
| `vowel_vortex` | 3×3 | All vowels, `{3}` quantifiers |
| `binary_blitz` | 3×3 | Binary (0/1) with character classes |
| `alpha_chaos` | 4×4 | Letter ranges `[A-D]`, `[E-H]`, etc. |

## Difficulty Levels

- **Level 1 (Easy)**: Simple character classes like `[A-F]`, `\d`, `.` wildcards
- **Level 2 (Medium)**: Alternations like `(A|B)`, character ranges like `[A-D]`
- **Level 3 (Hard)**: Negated classes, quantifiers like `{2}`, mixed patterns

## Character Sets

| Set | Characters | Description |
|-----|-----------|-------------|
| `hex` | 0-9 A-F | Hexadecimal digits (default) |
| `alpha` | A-Z | Uppercase letters |
| `digit` | 0-9 | Decimal digits |
| `vowel` | A E I O U | Vowels only |
| `alnum` | A-Z 0-9 | Letters and digits |
| `binary` | 0 1 | Binary digits |

## JSON Format

Puzzles exported as JSON follow this structure:

```json
{
  "name": "tutorial",
  "rows": 2,
  "cols": 2,
  "row_patterns": ["A.", ".1"],
  "col_patterns": ["A.", ".1"],
  "solution": [["A", "B"], ["C", "1"]],
  "charset": "ABC123",
  "version": "1.1.0"
}
```

You can share puzzles by sending the JSON file, and anyone can import them with `--import`.

## How It Works

### Puzzle Generation

1. A random grid of characters is generated from the chosen character set
2. Row and column regex patterns are derived from the solution characters
3. Pattern complexity is controlled by the difficulty level — easy patterns use literal characters and simple classes, while hard patterns use alternations and quantifiers
4. Every generated pattern is verified to match its corresponding solution row/column
5. Input validation ensures grid sizes (2–8) and difficulty (1–3) are within bounds

### Solving Algorithm

The solver uses **backtracking with constraint checking**:

1. Fill cells left-to-right, top-to-bottom
2. When a row is completed, validate it against the row regex
3. When a column is completed, validate it against the column regex
4. Backtrack immediately on constraint violations
5. This prunes the search space efficiently — invalid rows/columns are rejected as soon as they're completed
6. Invalid regex patterns are caught gracefully — the solver returns `False` rather than crashing

### Solution Uniqueness

The `count_solutions()` function searches for multiple solutions (up to a configurable limit). This lets you verify that a puzzle has a unique solution, which makes it more interesting to solve.

### Interactive Solver

The terminal UI provides real-time feedback:

- **Green** cells satisfy both their row and column regex
- **Yellow** cells satisfy their row regex only
- **Purple** cells satisfy their column regex only
- **Red** cells satisfy neither constraint
- Row/column patterns show ✓ (valid) or ✗ (invalid) status
- **Timer** tracks elapsed time from the first move
- **Move counter** increments each time you fill or clear a cell
- **Hint counter** increments each time you use H (hint) or S (solve)
- On completion, game statistics are displayed

## Running Tests

```bash
python3 test_regex_crossword.py
```

The test suite (45 tests) covers:

- Puzzle creation and validation
- Row/column constraint checking (including invalid regex patterns)
- All 6 predefined puzzles (valid solutions verified)
- Solver (backtracking and brute force)
- Random puzzle generation at all difficulty levels and charsets
- Interactive rendering (no crashes)
- Solution validation and error reporting
- JSON export/import roundtrip and error handling
- `count_solutions()` and `format_duration()`
- CLI flags (`--version`, `--help`, `--list`, `--export`, `--print`)
- Input validation for puzzle generation
- Binary charset support

## Example Session

```
$ python3 regex_crossword.py --timer --play easy

╔════════════════════════════════╗
║      REGEX CROSSWORD           ║
╚════════════════════════════════╝

  C1: /A1D/
  C2: /B2E/
  C3: /C3F/

     ┌────┬────┬────┐
 R1 │ ·  │ ·  │ ·  │  /ABC/
    ├────┼────┼────┤
 R2 │ ·  │ ·  │ ·  │  /123/
    ├────┼────┼────┤
 R3 │ ·  │ ·  │ ·  │  /DEF/
    └────┴────┴────┘

  R1: /ABC/ (partial)
  R2: /123/ (partial)
  R3: /DEF/ (partial)
  C1: /A1D/ (partial)
  C2: /B2E/ (partial)
  C3: /C3F/ (partial)

  Moves: 0  Hints: 0  Time: 0.0s
Controls: ↑↓←→=move  Type=fill  Del=clear  H=hint  S=solve  Q=quit  R=reset  Tab=next  T=timer
Cursor: Row 1, Col 1  Charset: ABCDEF123
```

Fill in the cells and watch them turn green as both row and column constraints are satisfied. When you complete the puzzle, you'll see:

```
🎉 CONGRATULATIONS! Puzzle solved! 🎉
  Moves: 9  Hints: 0  Time: 42.3s
```

## License

MIT