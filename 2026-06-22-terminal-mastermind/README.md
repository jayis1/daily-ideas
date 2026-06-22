# Terminal Mastermind

A beautiful, fully-featured **Mastermind code-breaking game** for the terminal, complete with colored pegs, multiple difficulty levels, an AI auto-solver using Knuth's minimax algorithm, game statistics tracking, and an interactive cursor-driven interface.

## What It Does

Mastermind is the classic board game where one player creates a secret color code and the other tries to crack it. After each guess, you receive feedback:

- **● Black peg** — correct color in the correct position
- **○ White peg** — correct color in the wrong position
- **· Empty** — no match

Use deduction and elimination to crack the code within the allowed number of guesses!

## Features

- 🎨 **Colored ANSI pegs** — vivid terminal colors for each code color
- 🎮 **Interactive play** — cursor-driven input with arrow keys, number keys, and letter keys
- 🤖 **AI Auto-Solver** — watch Knuth's minimax algorithm crack the code step by step
- 📊 **Benchmarking** — test the solver over hundreds of random games with statistics
- 📈 **Persistent stats** — track your games played, win rate, streaks, and average guesses
- 🔄 **Undo support** — take back your last guess
- 💡 **Hint system** — get a hint about one position's color
- ⚙️ **4 difficulty presets** — Easy, Medium, Hard, Expert
- 🎛️ **Custom configuration** — set code length (1–10) and color count (2–10)
- 🔒 **Custom secret codes** — set a specific code for challenges
- 🌱 **Seed support** — reproducible games with `--seed`
- ✅ **42 unit tests** — comprehensive test suite for game logic

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
python3 mastermind.py --difficulty hard      # 5 pegs, 8 colors
python3 mastermind.py --difficulty expert    # 6 pegs, 10 colors

# Custom configuration
python3 mastermind.py --code-length 5 --colors 7 --max-guesses 8

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

### Statistics

```bash
# View your game statistics
python3 mastermind.py --stats

# Reset statistics
python3 mastermind.py --reset-stats
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
| `Backspace` | Delete at cursor |
| `Enter` | Submit guess |
| `U` | Undo last guess |
| `H` | Get a hint (reveals one position) |
| `Q` | Quit game |

## Color Legend

| Key | Color | Symbol |
|-----|-------|--------|
| 1 | Red | R |
| 2 | Green | G |
| 3 | Blue | B |
| 4 | Yellow | Y |
| 5 | Magenta | M |
| 6 | Cyan | C |
| 7 | Orange | O |
| 8 | White | W |
| 9 | Purple | P |
| 0 | Pink | K |

## Difficulty Presets

| Difficulty | Code Length | Colors | Max Guesses |
|------------|-------------|--------|-------------|
| Easy | 4 | 6 | 12 |
| Medium | 4 | 8 | 10 |
| Hard | 5 | 8 | 10 |
| Expert | 6 | 10 | 10 |

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

  ✓ Solved in 5 guesses!
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

Game statistics are stored in `~/.mastermind_stats.json` and persist between sessions, tracking wins, streaks, and guess counts.

## License

MIT