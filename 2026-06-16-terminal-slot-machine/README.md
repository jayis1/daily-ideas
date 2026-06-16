# 🎰 Terminal Slot Machine

A fully-featured animated casino slot machine right in your terminal! Spin the reels, place bets, and chase the jackpot — all with colorful ANSI graphics and smooth animations. Available in both emoji and ASCII art modes.

## Features

- **3 spinning reels** with 8 weighted symbols (Cherry → Diamond) and staggered stop animations with bounce
- **5 paylines** — middle row, top row, bottom row, and both diagonals
- **2-of-a-kind small wins** on the main payline for near-miss excitement
- **Diagonal win highlighting** — diagonal wins now correctly flash their winning cells
- **Adjustable bets** (1–10 credits) with up/down controls
- **Credit management** — start with 100 credits, track your session stats
- **Smart rebuy** — press R when bankrupt; your bet is preserved if affordable, only lowered if necessary
- **Bankrupt detection** — get notified when you're out of credits
- **Auto-spin mode** — run `--auto N` to watch N spins play out automatically
- **Custom starting credits** — start with any amount via `--credits N`
- **Extended session statistics** — biggest win, peak credits, win/loss streaks, payback rate
- **Win celebrations** — flashing animations, jackpot screen flash for 💎💎💎
- **Two versions**: emoji mode (`slots.py`) for modern terminals, ASCII art mode (`slots_ascii.py`) for any terminal
- **Non-interactive demo** (`demo.py`) with configurable spins, credits, bet, and seed
- **CLI flags** — `--help`, `--version`, `--credits`, `--auto` on all scripts; `--bet` (max 10) and `--seed` on demo
- **Unit tests** — 21 tests covering game logic, payouts, paylines, edge cases, and bug regressions

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

## Paylines

The game evaluates **5 paylines** each spin:

1. **Middle row** (main payline, marked with arrows)
2. **Top row**
3. **Bottom row**
4. **Diagonal ↘** (top-left to bottom-right)
5. **Diagonal ↗** (bottom-left to top-right)

Each payline pays independently — you can win on multiple lines in a single spin! Diagonal wins now correctly highlight their winning cells in both the emoji and ASCII versions.

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

The demo simulates the same **5-payline win system** as the interactive game, producing accurate win rates and statistics.

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
| `R` | Rebuy (add 100 credits when bankrupt; bet preserved if affordable) |
| `Q` | Cash out and quit |

## CLI Flags

All scripts support the following flags:

| Flag | Description |
|------|-------------|
| `--help` | Show help message |
| `--version` | Show version number (v1.3.0) |
| `--credits N` | Set starting credits (default: 100, must be ≥ 1) |
| `--auto N` | Auto-spin N times (TUI scripts only, default: 0 = interactive, must be ≥ 0) |
| `--spins N` | Number of demo spins (demo.py only, default: 20, must be ≥ 1) |
| `--bet N` | Bet per spin (demo.py only, default: 1, must be 1–10) |
| `--seed N` | Random seed for reproducibility (demo.py only, default: 42) |

## How It Works

1. **Reel spinning**: Each reel is a weighted strip of symbols. When you press SPACE, the game pre-determines the outcome using weighted random selection, then animates each reel stopping in sequence (left → right) with a bounce effect.

2. **Win checking**: After all reels stop, the game evaluates 5 paylines (3 rows + 2 diagonals) for 3-of-a-kind matches, plus the middle row for 2-of-a-kind. Each match pays the symbol's multiplier × your bet.

3. **Win highlighting**: Winning cells flash green for horizontal payline wins. Diagonal wins now correctly highlight only the cells on the winning diagonal (top-left→bottom-right or bottom-left→top-right).

4. **Animations**: Winning cells flash green, jackpots flash the entire screen red/yellow, and reels bounce when they stop.

5. **Statistics**: The game tracks your session stats including total spins, total won, total bet, payback percentage, biggest single win, peak credits, best win streak, and worst loss streak — all shown in the exit summary.

## Known Issues

- The emoji version (`slots.py`) requires a terminal with Unicode and emoji support. If symbols appear garbled, use the ASCII version (`slots_ascii.py`).
- The `curses` library may not handle terminal resizing gracefully during gameplay.
- The demo (`demo.py`) generates independent random symbols per cell, while the TUI reels use adjacent strip positions. This means the probability distributions are slightly different between the two modes, though both use the same weighted symbol selection.

## File Structure

```
terminal-slot-machine/
├── slots.py          # Main game (emoji symbols, requires Unicode terminal)
├── slots_ascii.py    # Alternative game (ASCII art symbols, works anywhere)
├── demo.py           # Non-interactive demo with 5-payline simulation and stats
├── test_slots.py     # Unit tests for core game logic and bug regressions (21 tests)
└── README.md         # This file
```

## Changelog

### v1.3.0 — Bug Fix Release

- **Fixed**: Diagonal wins (↘ and ↗) now correctly highlight their winning cells in both `slots.py` and `slots_ascii.py`. Previously, only horizontal payline wins flashed; diagonal wins had line_ids 3 and 4 that never matched any row index (0–2), so they were invisible to the highlighting logic.
- **Fixed**: BELL ASCII art had inconsistent line widths — line 2 was 7 characters while lines 0 and 1 were 6 characters. All lines are now 6 characters for proper alignment.
- **Fixed**: `demo.py` payline line_ids were inconsistent with `slots.py`. The demo used line_ids 1–5 for the 5 paylines, while the TUI used 0–4. Now both use 0=top, 1=payline, 2=bottom, 3=diag↘, 4=diag↗. This ensures the win description labels (payline, top, bottom, diag↘, diag↗) are correct and consistent.
- **Fixed**: `demo.py` accepted `--bet` values above 10 (the TUI maximum). Now validates `--bet` must be 1–10.
- **Fixed**: `rebuy()` no longer unconditionally resets bet to 1. It now only lowers the bet if the new credits (100) can't cover the current bet. This means if you had bet=5 and go bankrupt, rebuying preserves your bet at 5 instead of resetting to 1.
- **Added**: 21 unit tests covering game logic, payline consistency, ASCII art consistency, demo bet validation, rebuy behavior, diagonal highlighting, and 2-of-a-kind detection.

### v1.2.0

- Fixed `rebuy()` to work when credits are positive but less than the current bet
- Fixed `demo.py` to evaluate all 5 paylines for 3-of-a-kind wins
- Fixed `demo.py` symbol frequency percentage calculation
- Added input validation for `--credits` and `--auto` flags
- Added environment variable parsing fallback for non-integer values
- Removed unused variables
- Added 7 new unit tests

### v1.1.0

- Added `--help`, `--version`, `--credits`, and `--auto` CLI flags
- Added bankrupt detection with rebuy option
- Added extended session statistics
- Added auto-spin mode
- Added exit summary screen
- Added comprehensive unit test suite (23 tests)
- Added docstrings and version number

## License

MIT — pull the lever and have fun!