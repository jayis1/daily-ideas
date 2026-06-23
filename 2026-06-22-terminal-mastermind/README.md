# Terminal Mastermind

A beautiful, fully-featured **Mastermind code-breaking game** for the terminal — with colored pegs, multiple difficulty levels, an AI auto-solver using Knuth's minimax algorithm, a scoring system, color-blind accessible mode, game timer, per-difficulty statistics, and an interactive cursor-driven interface.

## What It Does

Mastermind is the classic board game where one player creates a secret color code and the other tries to crack it. After each guess, you receive feedback:

- **● Black peg** — correct color in the correct position
- **○ White peg** — correct color in the wrong position
- **· Empty** — no match

Use deduction and elimination to crack the code within the allowed number of guesses!

## Features

- 🎨 **Colored ANSI pegs** — vivid terminal colors for each code color
- ♿ **Color-blind mode** (`--colorblind`) — distinct shape symbols for every color, no color reliance
- 🎮 **Interactive play** — cursor-driven input with arrow keys, number keys, and letter keys
- 🤖 **AI Auto-Solver** (`--solve`) — watch Knuth's minimax algorithm crack the code step by step
- 📊 **Benchmarking** (`--benchmark N`) — test the solver over hundreds of random games with guess distribution chart
- 📈 **Persistent stats** (`--stats`) — track your games played, win rate, streaks, and average guesses
- 📋 **Per-difficulty breakdown** — stats split by Easy/Medium/Hard/Expert
- 🕐 **Game timer** — elapsed time shown during play, toggle with `T` key
- 🏆 **Scoring system** — points based on guesses used, difficulty multiplier, and streak bonus
- 📜 **Game history** (`--history`) — review your last 50 games with scores and times
- 📖 **Rules display** (`--rules`) — in-terminal game rules and controls reference
- 🔄 **Undo support** — take back your last guess with `U`
- 💡 **Hint system** — get a hint about one position's color with `H`
- ⚙️ **4 difficulty presets** — Easy, Medium, Hard, Expert
- 🎛️ **Custom configuration** — set code length (1–10) and color count (2–10)
- 🔒 **Custom secret codes** — set a specific code for challenges
- 🌱 **Seed support** — reproducible games with `--seed`
- ✅ **79 unit tests** — comprehensive test suite for game logic, scoring, and formatting

## How to Install

```bash
# No external dependencies required — uses only Python 3 standard library
# Just clone and run!

git clone <repo-url>
cd terminal-mastermind
python3 mastermind.py
```

Requires Python 3.7+ with a terminal that supports ANSI escape codes (most modern terminals do).

## How to Run

### Interactive Game (default)

```bash
# Play with easy defaults (4 pegs, 6 colors, 12 guesses)
python3 mastermind.py

# Choose a difficulty
python3 mastermind.py --difficulty medium
python3 mastermind.py --difficulty hard       # 5 pegs, 8 colors
python3 mastermind.py --difficulty expert     # 6 pegs, 10 colors

# Custom configuration
python3 mastermind.py --code-length 5 --colors 7 --max-guesses 8

# Color-blind accessible mode
python3 mastermind.py --colorblind

# Set a specific secret code (for challenges)
python3 mastermind.py --secret "R G B Y"

# Reproducible game with seed
python3 mastermind.py --seed 42
```

### Auto-Solver Mode

Watch the AI solve the puzzle using Knuth's minimax algorithm:

```bash
# Watch the AI solve a random code
python3 mastermind.py --solve

# Solve a specific code
python3 mastermind.py --solve --secret "R G B Y"

# Solve on hard difficulty
python3 mastermind.py --solve --difficulty hard
```

### Benchmark Mode

Test the solver's performance over many random games:

```bash
# Benchmark 100 games at default difficulty
python3 mastermind.py --benchmark 100

# Benchmark at hard difficulty
python3 mastermind.py --benchmark 50 --difficulty hard
```

### Statistics & History

```bash
# View your game statistics (with per-difficulty breakdown)
python3 mastermind.py --stats

# View recent game history
python3 mastermind.py --history

# Reset statistics
python3 mastermind.py --reset-stats
```

### View Rules

```bash
python3 mastermind.py --rules
```

### Run Tests

```bash
python3 test_mastermind.py
```

## Controls (Interactive Mode)

| Key | Action |
|-----|--------|
| `1`–`9`, `0` | Place color at cursor position |
| `A`–`J` | Alternative color input (for colors beyond 9) |
| `←` / `→` | Move cursor left/right |
| `↑` / `↓` | Jump to first/last position |
| `Backspace` | Delete at cursor |
| `Enter` | Submit guess |
| `U` | Undo last guess |
| `H` | Get a hint (reveals one position) |
| `T` | Toggle timer display |
| `D` | Delete at cursor |
| `Q` | Quit game |

## Color Legend

| Key | Color | Symbol | Color-blind |
|-----|-------|--------|-------------|
| 1 | Red | R | ▲ |
| 2 | Green | G | ■ |
| 3 | Blue | B | ● |
| 4 | Yellow | Y | ★ |
| 5 | Magenta | M | ◆ |
| 6 | Cyan | C | ⬡ |
| 7 | Orange | O | ► |
| 8 | White | W | ○ |
| 9 | Purple | P | ✦ |
| 0 | Pink | K | ♦ |

## Scoring

| Difficulty | Multiplier | Code Length | Colors | Max Guesses |
|------------|------------|-------------|--------|-------------|
| Easy | ×1.0 | 4 | 6 | 12 |
| Medium | ×1.5 | 4 | 8 | 10 |
| Hard | ×2.0 | 5 | 8 | 10 |
| Expert | ×3.0 | 6 | 10 | 10 |

**Score formula:** `(max_guesses − guesses_used + 1) × 100 × difficulty_multiplier × streak_bonus`

Streak bonus: +10% per consecutive win (up to +100% at 10+ streak).

## Examples

### Auto-Solver Demo

```
$ python3 mastermind.py --solve --seed 42

  Mastermind — Auto-Solver (Knuth's Algorithm)
  Code length: 4  |  Colors: 6

  Secret:   C   R   R   C 
  ────────────────────────────────────────

  Turn 1:  R   R   G   G   ● ○ · ·
  Turn 2:  R   B   R   Y   ● ○ · ·
  Turn 3:  M   R   R   M   ● ● · ·
  Turn 4:  C   R   R   R   ● ● ● ·
  Turn 5:  C   R   R   C   ● ● ● ●

  ✓ Solved in 5 guesses!  Score: 800 pts
```

### Benchmark Results

```
$ python3 mastermind.py --benchmark 50

  Results:
    Games:      50
    Wins:       50 (100.0%)
    Avg turns:  4.48
    Min turns:  3
    Max turns:  6

  Guess Distribution:
    3 guesses:    2 ██
    4 guesses:   19 ███████████████████
    5 guesses:   28 ██████████████████████████████
    6 guesses:    1 █
```

## How It Works

### Game Logic

The evaluation algorithm uses the standard Mastermind scoring:
1. Count **black pegs**: positions where the guess exactly matches the secret
2. Count **total color matches** (intersection of color frequency counters)
3. **White pegs** = total color matches − black pegs

### Knuth's Algorithm

The auto-solver uses Donald Knuth's 1977 minimax algorithm:
1. Start with an initial guess (0, 0, 1, 1, ...)
2. After each guess, eliminate all impossible codes from the remaining set
3. Choose the next guess that minimizes the maximum size of the remaining possibility set
4. This guarantees solving any 4-peg, 6-color code in at most 5 guesses

### Statistics

Game statistics are stored in `~/.mastermind_stats.json` and persist between sessions, tracking wins, streaks, scores, and guess counts broken down by difficulty level. The last 50 games are kept as detailed history.

## What's New in v1.1.0

- **Scoring system** — earn points based on guesses, difficulty, and streaks
- **Color-blind mode** (`--colorblind`) — accessible symbols instead of color-only pegs
- **Game timer** — tracks and displays elapsed time during play
- **Per-difficulty stats** — breakdown of performance by difficulty level
- **Game history** (`--history`) — review your last 50 games
- **Rules display** (`--rules`) — in-terminal reference for controls and scoring
- **Input validation** — better error handling for invalid configs and secret codes
- **Up/Down arrow keys** — jump to first/last cursor position
- **Guess distribution** — benchmark mode now shows a histogram of guesses needed
- **Expanded test suite** — 79 tests covering all new features

## License

MIT