# Regex Crossword Generator & Solver

**v1.3.0** — A CLI tool for generating and solving **regex crossword puzzles** — a mind-bending puzzle type where each cell must satisfy both a row regex constraint and a column regex constraint simultaneously. Think of it as a cross between Sudoku and regular expressions!

## What is a Regex Crossword?

In a regex crossword, you fill a grid with characters where:

- Each **row** must match its corresponding regex pattern
- Each **column** must match its corresponding regex pattern
- Every cell sits at the intersection of a row and column, so it must satisfy **both** constraints

Example (2×2 tutorial puzzle):

```
        C1       C2
   ┌─────────┬─────────┐
R1 │  A  │  B  │   ← matches /AB/
   ├─────────┼─────────┤
R2 │  C  │  1  │   ← matches /C1/
   └─────────┴─────────┘
      ↑        ↑
   /AC/     /B1/
```

- Row 1 `AB` matches `/AB/` ✓
- Row 2 `C1` matches `/C1/` ✓
- Column 1 `AC` matches `/AC/` ✓
- Column 2 `B1` matches `/B1/` ✓

## Features

### Core Puzzles & Solving
- **6 built-in puzzles** of varying difficulty (all with verified unique solutions)
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

### Extended Features
- **Timer mode** (`--timer`) — tracks elapsed time while playing
- **Move counter** — tracks how many cells you've filled
- **Hint counter** — tracks how many hints/auto-solves you've used
- **Game statistics** — on completion, shows moves, hints, and time
- **JSON export** (`--export`) — export any puzzle as JSON for sharing
- **JSON import** (`--import`) — import and play puzzles from JSON files (with dimension validation)
- **Solution uniqueness checker** (`--unique`) — verify if a puzzle has a unique solution
- **Solution counter** (`count_solutions()`) — count the number of valid solutions (up to a limit)
- **`--version` flag** — display version number

## What's New

### v1.3.0 — Bug Fix Release
- **Fixed: Non-unique predefined puzzles** — Tutorial, binary_blitz, and vowel_vortex puzzles had multiple valid solutions, causing the solver to find a different answer than the stored one. All predefined puzzles now have verified unique solutions:
  - Tutorial: tightened from `/A./` and `/.1/` to `/AB/` and `/C1/` (literal patterns)
  - Medium: tightened from loose `[A-Z]{3}` patterns to `/A.C/`, `/E.G/` with literal column constraints, and reduced charset from 28 to 9 characters
  - Binary Blitz: tightened from `/0[01]{2}/` and `/[01]1[01]/` to `/0[01]0/` and `/011/`
  - Vowel Vortex: tightened from `/[AEIOU]{3}/` patterns (125+ solutions!) to `/AEI/`, `/OUA/`, `/EIO/` rows with `[AO]OE`, `[EI]UI`, `I[AO]O` columns (unique solution)
- **Fixed: `format_duration` negative values** — Previously returned negative strings like `-1.0s`; now clamps to `0.0s`
- **Fixed: `from_json` dimension mismatch crash** — JSON import with mismatched `rows`/`cols` and pattern/solution dimensions caused `IndexError` at runtime. Now validates dimensions and raises `ValueError` with a clear message
- **Added: `RegexCrossword.__post_init__` validation** — Creating a puzzle with mismatched dimensions (e.g., `rows=2` but only 1 `row_pattern`) now raises `ValueError` immediately instead of failing silently or crashing later
- **Added: 8 new regression tests** covering puzzle uniqueness, negative duration, JSON dimension validation, and constructor validation (60 total tests, all passing)

### v1.2.0 — Bug Fix Release
- Fixed crash with small charsets at difficulty 3
- Fixed `random.sample` crash with duplicate chars in charset
- Fixed variable shadowing in column validation
- Fixed regex metacharacters not escaped in negated classes
- Added input validation for charset
- Added 7 regression tests (52 total)

### v1.1.0 — Feature Release
- Timer mode, move/hint counters, game statistics
- JSON export/import, solution uniqueness checker
- 2 new built-in puzzles (binary_blitz, alpha_chaos)
- Binary charset, robust error handling

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
| `tutorial` | 2×2 | Literal patterns — great for learning |
| `easy` | 3×3 | Literal row/column strings |
| `medium` | 3×3 | Dot wildcards, `\d`, `[A-F]` character classes |
| `vowel_vortex` | 3×3 | Vowels only with character class columns |
| `binary_blitz` | 3×3 | Binary (0/1) with character classes |
| `alpha_chaos` | 4×4 | Letter ranges `[A-D]`, `[E-H]`, etc. |

All built-in puzzles have **verified unique solutions**.

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
  "row_patterns": ["AB", "C1"],
  "col_patterns": ["AC", "B1"],
  "solution": [["A", "B"], ["C", "1"]],
  "charset": "ABC123",
  "version": "1.3.0"
}
```

You can share puzzles by sending the JSON file, and anyone can import them with `--import`. The importer validates that dimensions, pattern counts, and solution sizes are all consistent — mismatched data will raise a clear `ValueError`.

## How It Works

### Puzzle Generation

1. A random grid of characters is generated from the chosen character set
2. Row and column regex patterns are derived from the solution characters
3. Pattern complexity is controlled by the difficulty level — easy patterns use literal characters and simple classes, while hard patterns use alternations and quantifiers
4. Every generated pattern is verified to match its corresponding solution row/column
5. Input validation ensures grid sizes (2–8) and difficulty (1–3) are within bounds
6. Charsets are validated to have at least 1 character (2 unique characters for difficulty 3)

### Solving Algorithm

The solver uses **backtracking with constraint checking**:

1. Fill cells left-to-right, top-to-bottom
2. When a row is completed, validate it against the row regex
3. When a column is completed, validate it against the column regex
4. Backtrack immediately on constraint violations
5. This prunes the search space efficiently — invalid rows/columns are rejected as soon as they're completed
6. Invalid regex patterns are caught gracefully — the solver returns `False` rather than crashing

### Solution Uniqueness

The `count_solutions()` function searches for multiple solutions (up to a configurable limit). All built-in puzzles are verified to have exactly **1 unique solution**. This makes them more satisfying to solve since there's only one correct answer.

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

The test suite (60 tests) covers:

- Puzzle creation, validation, and dimension checking
- Row/column constraint checking (including invalid regex patterns)
- All 6 predefined puzzles (valid unique solutions verified)
- Solver matches stored solution for all puzzles
- Puzzle uniqueness (tutorial, binary_blitz, vowel_vortex)
- Random puzzle generation at all difficulty levels and charsets
- Interactive rendering (no crashes)
- Solution validation and error reporting
- JSON export/import roundtrip and dimension validation
- `count_solutions()` and `format_duration()` (including edge cases)
- CLI flags (`--version`, `--help`, `--list`, `--export`, `--print`)
- Input validation for puzzle generation
- Binary charset support
- Small charset handling (binary at difficulty 3)
- Single-character and empty charset rejection
- Negated class regex validity across all charsets
- Variable shadowing fix verification (column validation)
- Negative duration handling
- Dimension mismatch detection in JSON import and constructor
- Version consistency

## Known Issues

- The `--unique` flag and `count_solutions()` can be very slow on puzzles with large grids and/or large character sets, as they exhaustively search all possible solutions. Use with smaller puzzles for best results.
- The interactive terminal UI requires a Unix-like system with `termios` support. On other systems, it falls back to text-only mode.

## Changelog

- **v1.3.0** — Bug fix release: fixed non-unique predefined puzzles (tutorial, medium, binary_blitz, vowel_vortex now all have verified unique solutions), fixed `format_duration` negative value handling, added dimension validation to `from_json` and `RegexCrossword.__post_init__` to prevent silent dimension mismatches, added 8 regression tests (60 total).
- **v1.2.0** — Bug fix release: fixed crashes with small charsets at difficulty 3, `random.sample` with duplicate chars, variable shadowing in column validation, regex metacharacters in negated classes, added charset input validation (52 tests).
- **v1.1.0** — Feature release: timer mode, move/hint counters, game statistics, JSON export/import, solution uniqueness checker, binary charset, 2 new puzzles.
- **v1.0.0** — Initial release: core puzzle generation, solving, interactive play, 4 built-in puzzles.

## License

MIT