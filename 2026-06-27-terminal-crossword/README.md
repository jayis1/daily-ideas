# 📝 Terminal Crossword Puzzle

An interactive crossword puzzle generator and player that runs entirely in the terminal. Features procedurally generated puzzles from a tech-themed word bank, beautiful box-drawing grid rendering with ANSI colors, and full keyboard-driven gameplay.

## ✨ Features

- **Procedural Generation** — Every puzzle is unique, built from a curated bank of 70+ tech and CS vocabulary words with clues
- **Interactive Gameplay** — Full keyboard-driven interface with arrow keys, letter input, and intuitive navigation
- **Smart Grid Rendering** — Beautiful Unicode box-drawing grid with clue numbers in cells, color-coded highlighting for cursor position, current word, checked cells, and revealed letters
- **Direction Toggle** — Switch between ACROSS and DOWN with Tab or Enter to fill words in either direction
- **Check & Reveal** — Check your answers for correctness (wrong cells highlighted in red), reveal individual letters, or reveal entire words
- **Clue Numbering** — Standard crossword numbering with separate ACROSS and DOWN clue lists, words marked as ✓ when completed
- **Reproducible Puzzles** — Use `--seed` to regenerate the same puzzle, or let it randomize
- **Two Display Modes** — Full interactive play mode, or static print mode (`--print`) for paper-style output
- **Answer Key** — `--answers` flag shows the solution alongside the puzzle

## 🎮 Controls

| Key | Action |
|-----|--------|
| Arrow keys | Move cursor between cells |
| A-Z | Type a letter in the current cell |
| Backspace | Delete current letter and move back |
| Tab / Enter | Toggle between ACROSS and DOWN |
| C | Check puzzle (marks correct/wrong cells) |
| R | Reveal the current letter |
| W | Reveal the entire current word |
| N | Generate a new puzzle |
| Q | Quit |

## 🔧 Installation

No external dependencies needed — just Python 3.6+:

```bash
# Clone or download the crossword.py file
# Make it executable:
chmod +x crossword.py
```

## 🚀 How to Run

### Interactive mode (default when running in a terminal)
```bash
python3 crossword.py
```

### Static print mode (for viewing the puzzle without interaction)
```bash
python3 crossword.py --print
```

### Show the answer key
```bash
python3 crossword.py --print --answers
```

### Specify a seed for reproducible puzzles
```bash
python3 crossword.py --seed 42
```

### Adjust difficulty (number of words)
```bash
python3 crossword.py --words 8    # Easier: fewer words
python3 crossword.py --words 18   # Harder: more words
```

### Force non-interactive mode (for piping output)
```bash
python3 crossword.py --no-interactive
```

## 📋 Usage Examples

**Play an interactive crossword:**
```
$ python3 crossword.py --seed 100

╔══════════════════════════════════════╗
║     📝 TERMINAL CROSSWORD PUZZLE      ║
╚══════════════════════════════════════╝

  Direction: ACROSS →  |  Words: 12  |  Hints: 0

   ┌───┬───┬───┬───┬───┬───┬───┬───┐
 0 │   │   │   │ 1 │   │   │   │   │
   │   │   │   │   │   │   │   │   │
   ├───┼───┼───┼───┼───┼───┼───┼───┤
 1 │   │ 2 │   │   │   │   │   │   │
   │   │   │   │   │   │   │   │   │
   ...

── ACROSS ──────────────────────────────
   1. A small part broken off from a larger whole (8)

── DOWN ────────────────────────────────
   1. Sequence where each number is the sum of the two before it (9)

── CONTROLS ────────────────────────────
  Arrow keys  Move cursor     Tab        Toggle across/down
  ...
```

**Print a puzzle with answers:**
```bash
python3 crossword.py --print --answers --seed 42
```

**Generate a daily puzzle (use date as seed):**
```bash
python3 crossword.py --seed $(date +%Y%m%d)
```

## 🧩 How It Works

1. **Word Selection** — Words are sorted by length (longest first) and shuffled with a random seed
2. **Placement** — The first word is placed horizontally in the center. Subsequent words are placed by finding intersecting letters with already-placed words
3. **Validation** — Each placement is checked for conflicts: no unintended words formed by adjacency, proper intersections, and no words running into each other
4. **Trimming** — After generation, the grid is trimmed to the minimal bounding box around all words
5. **Numbering** — Clue numbers are assigned in standard crossword order (top-to-bottom, left-to-right)

## 📐 Architecture

- `CrosswordGenerator` — Builds the puzzle grid from the word bank using constraint-based placement
- `CrosswordGame` — Manages interactive gameplay state (cursor, direction, filled letters, checking, revealing)
- `Colors` — ANSI color code constants for terminal rendering
- `print_puzzle()` — Static rendering function for non-interactive display
- `play_interactive()` — Full interactive terminal game loop with raw key input

## 🎯 Word Bank

The puzzle draws from 70+ tech-themed words including: ALGORITHM, PYTHON, BINARY, CACHE, DEBUG, ENCRYPT, FIBONACCI, KERNEL, MATRIX, RECURSION, STACK, and many more — all with descriptive clues that range from straightforward definitions to clever hints.