# Terminal Crossword Puzzle

A feature-rich interactive crossword puzzle generator and game for your terminal. Generates random tech-themed crossword puzzles and lets you play them right in the command line with color-coded feedback, hint system, save/load, and multiple difficulty levels.

## Features

- **Procedural Generation** — Creates unique crossword puzzles from a curated word bank of 80+ tech/computing terms
- **Interactive TUI Gameplay** — Full keyboard-driven interface with cursor navigation, letter typing, and real-time feedback
- **Color-Coded Cells** — Cyan cursor, blue highlighted word, green for correct, red for errors, yellow for revealed hints
- **Difficulty Levels** — Easy (8 words), Medium (12 words), Hard (18 words) with appropriate grid sizes
- **Progress Tracking** — Real-time percentage complete and elapsed timer display
- **Current Clue Display** — Shows the clue for the word under the cursor
- **Hint System** — Reveal a single letter (`R`) or an entire word (`W`)
- **Check Puzzle** — Validates all filled letters, marking correct (green) and incorrect (red)
- **Save & Resume** — Save game state to JSON and resume later with `--load`
- **Export to Text** — Export puzzles as plain-text files (no ANSI codes) with `--export`
- **Reproducible Seeds** — Use `--seed` to generate the same puzzle every time
- **Deduplication** — Handles duplicate word bank entries gracefully
- **Smart Grid Filling** — Validates no unintended parallel words are created during generation
- **Answer Mode** — Print puzzles with solutions using `--answers`
- **Graceful Fallback** — Works in non-interactive mode (piped output) when no TTY is available

## Installation

No external dependencies required — uses only Python standard library modules.

```bash
# Clone or download the script
git clone <repo-url>
cd terminal-crossword

# Run directly
python3 crossword.py
```

## Usage

### Play Interactively (default)

```bash
python3 crossword.py
```

### Set Difficulty

```bash
python3 crossword.py --difficulty easy    # 8 words, smaller grid
python3 crossword.py --difficulty medium   # 12 words (default)
python3 crossword.py --difficulty hard     # 18 words, larger grid
```

### Use a Seed for Reproducible Puzzles

```bash
python3 crossword.py --seed 42
```

### Print Puzzle (Non-Interactive)

```bash
python3 crossword.py --print
python3 crossword.py --print --answers     # Show solutions
```

### Export to Text File

```bash
python3 crossword.py --export puzzle.txt --seed 42
python3 crossword.py --export puzzle_answers.txt --answers --seed 42
```

### Save and Resume Games

```bash
# While playing, press S to save
# Resume later:
python3 crossword.py --load ~/.crossword_saves/crossword_20260627_143000.json
```

### Override Word Count

```bash
python3 crossword.py --words 20    # Override difficulty default
```

### Show Version

```bash
python3 crossword.py --version
```

## Controls

| Key | Action |
|-----|---------|
| Arrow keys | Move cursor |
| Tab / Enter | Toggle across/down direction |
| A-Z | Type a letter |
| Backspace | Delete letter / move back |
| C | Check puzzle (marks correct/incorrect) |
| R | Reveal current letter (hint) |
| W | Reveal current word (hint) |
| S | Save game to file |
| N | Start a new puzzle |
| Q | Quit |

## Example Output

```
==========================================
  TERMINAL CROSSWORD PUZZLE
==========================================

  Direction: ACROSS →  |  Words: 12  |  Progress: 23%  |  Hints: 0  |  Time: 01:15

  > 3A: A step-by-step procedure for solving a problem

  [  ][1 ][  ][  ][  ][  ][  ][  ][  ][  ]
  ...
```

## Running Tests

```bash
python3 test_crossword.py
```

The test suite covers:
- Grid generation and word placement validation
- Seed reproducibility
- Difficulty presets
- Game mechanics (typing, backspace, reveal, check)
- Save/load round-trip
- Edge cases (tiny grids, empty words, boundary checks)
- Progress tracking and timer formatting
- Export functionality (ANSI-free output)
- Version metadata

## Architecture

- **`CrosswordGenerator`** — Generates crossword grids from the word bank, validates placements, trims bounding boxes, and serializes/deserializes state
- **`CrosswordGame`** — Manages interactive game state: player grid, cursor, direction, checking, hints, progress, rendering
- **`play_interactive()`** — Main game loop with terminal raw-mode input handling
- **`print_puzzle()`** — Static ANSI-color printed output for non-interactive mode
- **`WORD_BANK`** — 80+ (word, clue) tuples with tech/computing terms
- **`DIFFICULTY_PRESETS`** — Configuration dict for easy/medium/hard modes

## License

MIT