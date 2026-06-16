# 🎰 Terminal Slot Machine

A fully-featured animated casino slot machine right in your terminal! Spin the reels, place bets, and chase the jackpot — all with colorful ANSI graphics and smooth animations. Available in both emoji and ASCII art modes.

## Features

- **3 spinning reels** with 8 weighted symbols (Cherry → Diamond) and staggered stop animations with bounce
- **5 paylines** — middle row, top row, bottom row, and both diagonals
- **2-of-a-kind small wins** on the main payline for near-miss excitement
- **Adjustable bets** (1–10 credits) with up/down controls
- **Credit management** — start with 100 credits, track your session stats
- **Bankrupt detection** — get notified when you're out of credits, press R to rebuy
- **Auto-spin mode** — run `--auto N` to watch N spins play out automatically
- **Custom starting credits** — start with any amount via `--credits N`
- **Extended session statistics** — biggest win, peak credits, win/loss streaks, payback rate
- **Win celebrations** — flashing animations, jackpot screen flash for 💎💎💎
- **Two versions**: emoji mode (`slots.py`) for modern terminals, ASCII art mode (`slots_ascii.py`) for any terminal
- **Non-interactive demo** (`demo.py`) with configurable spins, credits, bet, and seed
- **CLI flags** — `--help`, `--version`, `--credits`, `--auto` on all scripts
- **Unit tests** — 23 tests covering game logic, payouts, and statistics

## Symbol Pay Table

| Symbol | 3-of-a-Kind Multiplier | Weight |
|--------|----------------------:|-------:|
| 🍒 Cherry | ×3 | 8 |
| 🍋 Lemon | ×4 | 7 |
| 🍊 Orange | ×5 | 6 |
| 🍇 Plum | ×8 | 5 |
| 🔔 Bell | ×15 | 4 |
| 📊 Bar | ×25 | 3 |
| 7️⃣ Seven | ×50 | 2 |
| 💎 Diamond | ×100 | 1 |

All payouts are multiplied by your current bet. 2-of-a-kind on the payline pays 1/5 of the 3-of-a-kind rate (minimum ×1).

## How to Install

No external dependencies — uses only Python's standard library (`curses`).

```bash
# Just clone and run
git clone <repo-url>
cd terminal-slot-machine
```

Requires Python 3.7+ with `curses` support (included on Linux/macOS; on Windows, install `windows-curses`).

## How to Run

### Interactive (Emoji mode — best on modern terminals)
```bash
python3 slots.py                    # Default: 100 credits
python3 slots.py --credits 500      # High-roller: start with 500
python3 slots.py --auto 20          # Auto-spin 20 times
```

### Interactive (ASCII art mode — works everywhere)
```bash
python3 slots_ascii.py              # Default: 100 credits
python3 slots_ascii.py --credits 500
python3 slots_ascii.py --auto 20
```

### Non-interactive demo (prints results to stdout)
```bash
python3 demo.py                     # Default: 20 spins, seed=42
python3 demo.py --spins 50          # 50 spins
python3 demo.py --credits 200 --bet 3  # Custom credits and bet
python3 demo.py --seed 12345         # Reproducible results
```

### Run the tests
```bash
python3 -m pytest test_slots.py -v
```

## Controls

| Key | Action |
|-----|--------|
| `SPACE` / `S` | Spin the reels |
| `↑` / `+` | Increase bet (max 10) |
| `↓` / `-` | Decrease bet (min 1) |
| `R` | Rebuy (add 100 credits when bankrupt) |
| `Q` | Cash out and quit |

## CLI Flags

All scripts support the following flags:

| Flag | Description |
|------|-------------|
| `--help` | Show help message |
| `--version` | Show version number (v1.1.0) |
| `--credits N` | Set starting credits (default: 100) |
| `--auto N` | Auto-spin N times (TUI scripts only, default: 0 = interactive) |
| `--spins N` | Number of demo spins (demo.py only, default: 20) |
| `--bet N` | Bet per spin (demo.py only, default: 1) |
| `--seed N` | Random seed for reproducibility (demo.py only, default: 42) |

## How It Works

1. **Reel spinning**: Each reel is a weighted strip of symbols. When you press SPACE, the game pre-determines the outcome using weighted random selection, then animates each reel stopping in sequence (left → right) with a bounce effect.

2. **Win checking**: After all reels stop, the game evaluates 5 paylines (3 horizontal + 2 diagonal) for 3-of-a-kind matches, plus 2-of-a-kind on the middle row. Each match pays the symbol's multiplier × your bet.

3. **Animations**: Winning cells flash green, jackpots flash the entire screen red/yellow, and reels bounce when they stop.

4. **Statistics**: The game tracks your session stats including total spins, total won, total bet, payback percentage, biggest single win, peak credits, best win streak, and worst loss streak — all shown in the exit summary.

## Example Demo Output

```
🎰 LUCKY TERMINAL SLOTS — Demo Mode 🎰
=======================================================

  Starting credits: 100
  Bet per spin:     1
  Number of spins:  20
  Random seed:      42

  Spin    Reel 1    Reel 2    Reel 3  Result                           Credits
  ---------------------------------------------------------------------------
     1         🍒         🍒         🍊  ✨ WIN 2× 🍒 → ×1 (1)                  100
     2         🍊         🍋         🍋  ✨ WIN 2× 🍋 → ×1 (1)                  100
     3         🍒       7️⃣         🍒  —                                     99
  ...

=======================================================
  SESSION SUMMARY
=======================================================
  Final credits:     86
  Total spins:       20
  Total bet:         20
  Total won:         6
  Payback rate:      30.0%
  Net profit/loss:   -14
  Wins:              6  |  Losses: 14
  Biggest win:       1
  Best win streak:   2
  Worst loss streak: 7

  Symbol frequency:
    🍒 CHERRY     19 ( 31.7%) ███████████████
    🍋 LEMON      12 ( 20.0%) ██████████
    ...
```

## File Structure

```
terminal-slot-machine/
├── slots.py          # Main game (emoji symbols, requires Unicode terminal)
├── slots_ascii.py    # Alternative game (ASCII art symbols, works anywhere)
├── demo.py           # Non-interactive demo with rich stats output
├── test_slots.py     # Unit tests for core game logic (23 tests)
└── README.md         # This file
```

## Changelog

### v1.1.0
- Added `--help`, `--version`, `--credits`, and `--auto` CLI flags to TUI scripts
- Added `--spins`, `--bet`, and `--seed` CLI flags to demo.py
- Added bankrupt detection with rebuy option (press R)
- Added extended session statistics: biggest win, peak credits, win/loss streaks
- Added auto-spin mode for hands-free play
- Added exit summary screen showing full session stats
- Added input validation and error messages for bet limits
- Enhanced demo.py with formatted table output, symbol frequency chart, and session summary
- Added comprehensive unit test suite (23 tests)
- Added docstrings and version number to all modules

## License

MIT — pull the lever and have fun!