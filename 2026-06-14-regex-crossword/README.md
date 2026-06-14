# Regex Crossword Generator & Solver

A CLI tool for generating and solving **regex crossword puzzles** — a mind-bending puzzle type where each cell must satisfy both a row regex constraint and a column regex constraint simultaneously. Think of it as a cross between Sudoku and regular expressions!

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

- **4 built-in puzzles** of varying difficulty (tutorial, easy, medium, vowel vortex)
- **Random puzzle generation** with configurable grid size (2×2 to 6×6)
- **3 difficulty levels** controlling regex complexity (simple literals → alternations → quantifiers)
- **5 character sets**: hex (0-9, A-F), alpha (A-Z), digits, vowels, alphanumeric
- **Interactive terminal UI** with:
  - Arrow key navigation
  - Real-time constraint validation (green = both constraints met, yellow = row only, purple = column only, red = neither)
  - Row/column pattern status indicators (✓/✗)
  - Auto-advance after typing a character
  - Hint system (reveal a cell) and auto-solve
- **Programmatic solver** using backtracking with constraint checking
- **Brute force solver** for verification
- **Solution validator** that checks all regex constraints

## Installation

No external dependencies needed — uses only Python standard library (3.7+).

```bash
# Clone or download the project
cd regex-crossword

# Run directly
python3 regex_crossword.py --help
```

## Usage

### Play a built-in puzzle interactively

```bash
python3 regex_crossword.py --play tutorial
python3 regex_crossword.py --play easy
python3 regex_crossword.py --play medium
python3 regex_crossword.py --play vowel_vortex
```

### Generate a random puzzle

```bash
# 3×3 grid, easy difficulty, hex charset
python3 regex_crossword.py --generate 3 3

# 4×4 grid, medium difficulty, alpha charset  
python3 regex_crossword.py --generate 4 4 --diff 2 --charset alpha

# 5×5 grid, hard difficulty, digits only
python3 regex_crossword.py --generate 5 5 --diff 3 --charset digit --verify
```

### Print a puzzle in text mode

```bash
python3 regex_crossword.py --print tutorial
python3 regex_crossword.py --print easy
```

### Solve a puzzle and show the answer

```bash
python3 regex_crossword.py --solve tutorial
python3 regex_crossword.py --solve medium
```

### List available puzzles

```bash
python3 regex_crossword.py --list
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
| R | Reset (clear all cells) |
| Q | Quit |

## Built-in Puzzles

| Name | Size | Description |
|------|------|-------------|
| `tutorial` | 2×2 | Simple dot-matching patterns |
| `easy` | 3×3 | Literal row/column strings |
| `medium` | 3×3 | Character classes and quantifiers |
| `vowel_vortex` | 3×3 | All vowels, `{3}` quantifiers |

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

## How It Works

### Puzzle Generation

1. A random grid of characters is generated from the chosen character set
2. Row and column regex patterns are derived from the solution characters
3. Pattern complexity is controlled by the difficulty level — easy patterns use literal characters and simple classes, while hard patterns use alternations and quantifiers
4. Every generated pattern is verified to match its corresponding solution row/column

### Solving Algorithm

The solver uses **backtracking with constraint propagation**:

1. Fill cells left-to-right, top-to-bottom
2. When a row is completed, validate it against the row regex
3. When a column is completed, validate it against the column regex
4. Backtrack immediately on constraint violations
5. This prunes the search space efficiently — invalid rows/columns are rejected as soon as they're completed

### Interactive Solver

The terminal UI provides real-time feedback:

- **Green** cells satisfy both their row and column regex
- **Yellow** cells satisfy their row regex only
- **Purple** cells satisfy their column regex only
- **Red** cells satisfy neither constraint
- Row/column patterns show ✓ (valid) or ✗ (invalid) status

## Running Tests

```bash
python3 test_regex_crossword.py
```

The test suite covers:

- Puzzle creation and validation
- Row/column constraint checking
- All predefined puzzles (valid solutions verified)
- Solver (backtracking and brute force)
- Random puzzle generation at all difficulty levels and charsets
- Interactive rendering (no crashes)
- Solution validation

## Example Session

```
$ python3 regex_crossword.py --play easy

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

Controls: ↑↓←→=move  Type=fill  Del=clear  H=hint  S=solve  Q=quit  R=reset  Tab=next
Cursor: Row 1, Col 1  Charset: ABCDEF123
```

Type `A`, `B`, `C` for row 1, `1`, `2`, `3` for row 2, `D`, `E`, `F` for row 3, and watch the cells turn green as both row and column constraints are satisfied!

## License

MIT