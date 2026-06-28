# Terminal Crossword Puzzle

A feature-rich interactive crossword puzzle generator and game for your terminal. Creates random tech-themed crossword puzzles you can play right in the command line — with color-coded feedback, hints, save/resume, themed word banks, puzzle statistics, and multiple difficulty levels.

## Features

- **Procedural Generation** — Creates unique crossword puzzles from a curated word bank of 76+ tech/computing terms
- **Interactive TUI Gameplay** — Full keyboard-driven interface with cursor navigation, letter typing, and real-time feedback
- **Color-Coded Cells** — Cyan cursor, blue highlighted word, green for correct, red for errors, yellow for revealed hints
- **Difficulty Levels** — Easy (8 words), Medium (12 words), Hard (18 words) with appropriate grid sizes
- **Themed Puzzles** — `--theme programming|networking|data|systems` filters the word bank by topic
- **Puzzle Statistics** — `--stats` shows word count, intersections, grid density, average word length, and more
- **Progress Tracking** — Real-time percentage complete and elapsed timer (with hours support for long sessions)
- **Current Clue Display** — Shows the clue for the word under the cursor
- **Hint System** — Reveal a single letter (`R`) or an entire word (`W`)
- **Check Puzzle** — Validates all filled letters, marking correct (green) and incorrect (red)
- **Save & Resume** — Save game state to JSON and resume later with `--load`
- **List Saves** — `--list-saves` shows all saved games with version info
- **Export to Text** — Export puzzles as plain-text files (no ANSI codes) with `--export`
- **Reproducible Seeds** — Use `--seed` to generate the same puzzle every time
- **No-Color Mode** — `--no-color` or `NO_COLOR=1` env var disables all ANSI output
- **Deduplication** — Handles duplicate word bank entries gracefully
- **Smart Grid Filling** — Validates no unintended parallel words are created during generation
- **Answer Mode** — Print puzzles with solutions using `--answers`
- **Graceful Fallback** — Works in non-interactive mode (piped output) when no TTY is available
- **Empty Grid Handling** — Gracefully handles edge cases like empty grids or zero-word puzzles
- **Version Compatibility** — Save files include version info; version mismatches are warned but still loaded
- **Recursive-Free Main Loop** — New puzzle generation uses a loop instead of recursive `main()` calls

## Installation

No external dependencies — uses only Python standard library modules.

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

### Play a Themed Puzzle

```bash
python3 crossword.py --theme programming   # Programming terms only
python3 crossword.py --theme networking    # Networking terms only
python3 crossword.py --theme data         # Data structure terms only
python3 crossword.py --theme systems      # OS/systems terms only
```

### Use a Seed for Reproducible Puzzles

```bash
python3 crossword.py --seed 42
```

### View Puzzle Statistics

```bash
python3 crossword.py --stats --seed 42
```

Output:
```
==========================================
  PUZZLE STATISTICS
==========================================

  Total words:     12
  Across words:    8
  Down words:       4
  Total cells:      83
  Intersections:    12
  Grid density:     29.6%
  Avg word length:  7.9
  Longest word:     RECURSION (9 letters)
  Shortest word:    GATEWAY (7 letters)
```

### Print Puzzle (Non-Interactive)

```bash
python3 crossword.py --print
python3 crossword.py --print --answers     # Show solutions
```

### Disable Color Output

```bash
python3 crossword.py --no-color            # CLI flag
NO_COLOR=1 python3 crossword.py --print   # Environment variable
```

### Export to Text File

```bash
python3 crossword.py --export puzzle.txt --seed 42
python3 crossword.py --export puzzle_answers.txt --answers --seed 42
```

### Save and Resume Games

```bash
# While playing, press S to save
# List saved games:
python3 crossword.py --list-saves

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
|-----|--------|
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

   1 C O M P 1 0 L E  3 W I R 5 E L E S S
     O       O       I         I
     M       B       R         B
   4 A L G O R I T H M     F 6 B O O L E A N
     I       O       I         O
     L       L       S         L
     E       G       S         E
```

## Running Tests

```bash
python3 test_crossword.py
```

The test suite covers 88 tests including:
- Grid generation and word placement validation
- Seed reproducibility
- Difficulty presets
- Themed word bank filtering and generation
- Game mechanics (typing, backspace, reveal, check)
- Save/load round-trip (including version field)
- Statistics (`get_stats`, `print_stats`)
- Timer formatting (MM:SS and HH:MM:SS)
- Export functionality (ANSI-free output)
- `--no-color` and `NO_COLOR` env var support
- `strip_ansi` utility function
- Version metadata
- Render side-effect prevention (direction, message_timer)
- Double-digit clue number rendering
- Empty puzzle graceful handling
- Missing save file error handling

## Architecture

- **`CrosswordGenerator`** — Generates crossword grids from the word bank, validates placements, trims bounding boxes, computes statistics, and serializes/deserializes state
- **`CrosswordGame`** — Manages interactive game state: player grid, cursor, direction, checking, hints, progress, rendering
- **`play_interactive()`** — Main game loop with terminal raw-mode input handling (non-recursive for new puzzles)
- **`print_puzzle()`** — Static ANSI-color printed output for non-interactive mode (supports `use_color` parameter)
- **`print_stats()`** — Display puzzle metrics (word count, intersections, density, etc.)
- **`get_themed_word_bank()`** — Returns filtered word bank for a given theme
- **`WORD_BANK`** — 76+ (word, clue) tuples with tech/computing terms
- **`THEMED_WORDS`** — Theme-to-word-list mappings (programming, networking, data, systems)
- **`DIFFICULTY_PRESETS`** — Configuration dict for easy/medium/hard modes

## Changelog

### v1.3.0 — Feature Enhancements
- **Added themed puzzles** — `--theme` flag supports programming, networking, data, and systems word banks
- **Added puzzle statistics** — `--stats` shows word count, intersections, grid density, avg/longest/shortest word lengths
- **Added `--list-saves`** — Lists all saved games with version info
- **Added `--no-color` flag** — Explicitly disable ANSI output; also respects `NO_COLOR` env var
- **Added `strip_ansi()` utility** — Strips ANSI escape codes from strings
- **Added `print_puzzle()` `use_color` parameter** — Explicit color control for non-interactive mode
- **Added `get_stats()` method** — Compute puzzle metrics programmatically
- **Added custom word bank support** — `CrosswordGenerator` now accepts `word_bank` parameter
- **Added version field to save files** — Saved games include `version` key for compatibility
- **Added version mismatch warning** — `load_game()` warns when save file version differs from current
- **Added hours support to timer** — `format_time()` shows HH:MM:SS when elapsed > 1 hour
- **Fixed recursive main()** — New puzzle generation uses a `while` loop instead of recursive `main()` call
- **Added 28 new tests** — Covering themes, stats, timer formatting, color control, strip_ansi, save version, and more

### v1.2.0 — Bug Fixes
- **Fixed infinite recursion** in `get_current_word_cells()` on empty grids
- **Fixed render side effect** — `render()` no longer toggles direction or decrements `message_timer`
- **Fixed `generate(max_words=0)`** — Now correctly places zero words
- **Fixed grid misalignment** with double-digit clue numbers
- **Fixed crash on empty puzzle** — Shows "No puzzle" message instead of crashing
- **Removed unused imports** — `copy` and `defaultdict`

## License

MIT