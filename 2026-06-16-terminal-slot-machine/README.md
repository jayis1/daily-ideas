# 🎰 Terminal Slot Machine

A fully-featured animated casino slot machine right in your terminal! Spin the reels, place bets, and chase the jackpot — all with colorful ANSI graphics and smooth animations.

## Features

- **3 spinning reels** with 8 weighted symbols (Cherry → Diamond) and staggered stop animations with bounce
- **5 paylines** — middle row, top row, bottom row, and both diagonals
- **2-of-a-kind small wins** on the main payline for near-miss excitement
- **Adjustable bets** (1–10 credits) with up/down controls
- **Credit management** — start with 100 credits, track your session stats
- **Win celebrations** — flashing animations, jackpot screen flash for 💎💎💎
- **Two versions**: emoji mode (`slots.py`) for modern terminals, ASCII art mode (`slots_ascii.py`) for any terminal
- **Non-interactive demo** (`demo.py`) for quick results without a TUI
- **Session statistics** — spin count, total won, payback percentage

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
python3 slots.py
```

### Interactive (ASCII art mode — works everywhere)
```bash
python3 slots_ascii.py
```

### Non-interactive demo (prints 20 spins to stdout)
```bash
python3 demo.py
```

## Controls

| Key | Action |
|-----|--------|
| `SPACE` / `S` | Spin the reels |
| `↑` / `+` | Increase bet (max 10) |
| `↓` / `-` | Decrease bet (min 1) |
| `Q` | Cash out and quit |

## How It Works

1. **Reel spinning**: Each reel is a weighted strip of symbols. When you press SPACE, the game pre-determines the outcome using weighted random selection, then animates each reel stopping in sequence (left → right) with a bounce effect.

2. **Win checking**: After all reels stop, the game evaluates 5 paylines (3 horizontal + 2 diagonal) for 3-of-a-kind matches, plus 2-of-a-kind on the middle row. Each match pays the symbol's multiplier × your bet.

3. **Animations**: Winning cells flash green, jackpots flash the entire screen red/yellow, and reels bounce when they stop.

## Example Demo Output

```
🎰 LUCKY TERMINAL SLOTS — Demo Mode 🎰
==================================================

Starting credits: 100
Bet per spin: 1

Spin   1: 🍒 🍒 🍊  ✨ WIN 2× 🍒 → ×1 (+1)
Spin   2: 🍊 🍋 🍋  ✨ WIN 2× 🍋 → ×1 (+1)
Spin   3: 🍒 7️⃣ 🍒  —
...
```

## File Structure

```
terminal-slot-machine/
├── slots.py          # Main game (emoji symbols, requires Unicode terminal)
├── slots_ascii.py    # Alternative game (ASCII art symbols, works anywhere)
├── demo.py           # Non-interactive demo (20 spins, prints to stdout)
├── test_slots.py     # Unit test for core game logic
└── README.md         # This file
```

## License

MIT — pull the lever and have fun!