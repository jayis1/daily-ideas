# ⌨️ Terminal Typing Racer

A fast-paced typing game that runs entirely in your terminal. Words fall from the top of the screen — type them before they hit the danger zone! Features progressive difficulty, combo multipliers, power-ups, particle explosions, persistent high scores, and real-time WPM tracking.

```
  ♥ ♥ ♥ ♡ ♡  |  Score: 850  |  Combo: 5x  |  WPM: 62  |  Acc: 94%  |  Lv3
  ──────────────────────────────────────────────────────────────────────────────
         crystal
                    phantom
              blaze
     storm                  ←  ▼ target arrow
                    swift
   ──────────────────────────────────────────────────────────────────────────────
  Keys: B C P S W                        >> sw|ift
```

## 🎮 How It Works

Words appear at the top of the screen and fall downward. Type the words to destroy them before they reach the red danger zone at the bottom. As you complete words, the game gets progressively harder:

- **New difficulty tiers unlock** as you complete more words (easy → medium at 3, hard at 10, expert at 20)
- **Speed increases** with each level (every 8 words completed)
- **Spawn rate accelerates** the longer you survive
- **Combo system** rewards consecutive correct completions with score multipliers
- **Power-ups** appear periodically — collect them for Freeze, Bomb, or extra Life

When a word reaches the danger zone, you lose a life (♥). Lose all 5 lives and it's game over. Your score is saved to a persistent leaderboard.

## ✨ Features

### Core Gameplay
- **Progressive difficulty** — 4 word tiers unlock as you improve (easy, medium, hard, expert)
- **Smart targeting** — automatically locks onto the most urgent word matching your first keystroke
- **Combo system** — chain completions for score multipliers (each combo adds 0.25x)
- **Combo milestones** — visual notification at every 5x combo streak
- **Target arrow** — a ▼ indicator points at your current target word

### Power-Ups (new!)
- **❄ Freeze** — freezes all falling words for 3 seconds, giving you time to catch up
- **💥 Bomb** — destroys all words currently on screen (resets your combo)
- **♥ +1 Life** — restores one life (up to a max of 5)

Power-ups spawn every 6–12 words and fall slowly down the screen. They're shown as `[FREEZE]`, `[BOMB]`, or `[+1 LIFE]` — walk into them (they fall toward you naturally).

### Visual & Stats
- **Particle explosions** — completed words burst into character particles with gravity physics
- **Real-time WPM** — tracks your words-per-minute as you play
- **Accuracy tracking** — shows your correct keystroke percentage
- **Danger zone** — words glow red as they approach the bottom; freeze tint when power-up active
- **Key hints** — shows available first letters for untyped words at the bottom of the screen
- **Level-up flash** — visual notification when you level up or unlock a new tier

### Meta Features
- **Persistent high scores** — top 10 scores saved to `.typing_racer_scores.json`
- **3-second countdown** — gives you time to get ready before words start falling
- **Pause screen** — press ESC to pause; shows current stats
- **Terminal resize handling** — adapts if you resize your terminal mid-game
- **Minimum size check** — warns if your terminal is too small (needs 60×20 minimum)

## 🚀 Installation

No external dependencies — uses only Python's standard library (`curses`, `json`, `argparse`).

```bash
# Clone and run
cd ~/daily-ideas/2026-06-15-typing-racer
python3 typing_racer.py
```

### Requirements
- Python 3.10+
- A terminal with color support (most modern terminals: iTerm2, Windows Terminal, gnome-terminal, etc.)
- Terminal size at least 60×24 recommended (minimum 60×20)

## 🕹️ Controls

| Key | Action |
|-----|--------|
| `A-Z`, `a-z` | Type letters to destroy falling words |
| `ESC` | Pause / Resume |
| `R` | Restart (on game over screen) |
| `Q` | Quit (on game over screen) |
| `Ctrl+C` | Force quit anytime |

## 📋 CLI Options

```bash
python3 typing_racer.py              # Start the game
python3 typing_racer.py --help       # Show help and usage info
python3 typing_racer.py --version    # Show version (2.0.0)
python3 typing_racer.py --scores     # Show high scores leaderboard
python3 typing_racer.py --reset       # Reset all high scores
```

## 📖 Gameplay Tips

1. **Prioritize low words** — the game auto-selects the word closest to the danger zone that matches your first keystroke
2. **Build combos** — consecutive completions give increasing score multipliers (each combo adds 0.25x, so a 5x combo = 2.0x multiplier)
3. **Watch for red words** — words in the danger zone glow red; focus on those first
4. **Expert words are worth 5x** — harder words give much more score, but are longer and faster
5. **Accuracy matters** — mistyped keys break your combo, so type carefully
6. **Grab power-ups** — Freeze is great for catching up, Bomb clears a crowded screen
7. **Check key hints** — the "Keys:" line at the bottom shows which first letters are currently available

## 📊 Scoring

```
Points = (10 + word_length) × combo_multiplier × difficulty_bonus
```

| Difficulty | Bonus | Example Words |
|-----------|-------|--------------|
| Easy      | 1x    | cat, dog, sun |
| Medium    | 2x    | flame, storm, tiger |
| Hard      | 3x    | phoenix, cascade, phantom |
| Expert    | 5x    | magnificent, constellation, serendipity |

## 🧪 Testing

```bash
# Run all tests
python3 -m pytest test_typing_racer.py -v

# Or with unittest directly
python3 test_typing_racer.py
```

The test suite covers 38 tests including:
- `FallingWord` — initialization, typing, completion, freezing
- `Particle` — physics, lifetime
- `PowerUp` — types, expiration, symbols
- `HighScoreManager` — add, save, load, sort, clear, corrupt-file handling
- Word pool validation — lowercase, no duplicates, appropriate lengths
- Scoring formula verification
- Version format check

## 🏗️ Architecture

| Class | Purpose |
|-------|---------|
| `FallingWord` | A word falling down the screen with typing progress state |
| `Particle` | Simple physics particle for explosion effects |
| `PowerUp` | Collectible power-up (Freeze / Bomb / Heart) |
| `HighScoreManager` | JSON-based persistent leaderboard (top 10) |
| `TypingRacer` | Main game class — spawning, input, physics, rendering, game loop |

All rendering uses `curses` — no external UI library needed. The game loop uses delta-time updates (capped at 100ms) for consistent physics across different frame rates.

## 🆕 What's New in v2.0

- **Power-ups**: Freeze (❄), Bomb (💥), and Heart (♥) collectibles spawn during gameplay
- **Persistent high scores**: Top 10 scores saved to `.typing_racer_scores.json`
- **Countdown start**: 3-second countdown before the game begins, with title screen showing high scores
- **Pause screen**: Shows current stats (score, WPM, accuracy, combo, lives)
- **Key hints**: Available first letters displayed at the bottom of the screen
- **Combo milestones**: Visual notification at every 5x combo streak
- **Target arrow**: ▼ indicator above your currently targeted word
- **Freeze visual effect**: Blue tint overlay when freeze power-up is active
- **Terminal resize handling**: Adapts to size changes mid-game
- **Minimum terminal size check**: Warns if window is too small
- **CLI flags**: `--help`, `--version`, `--scores`, `--reset`
- **Level display**: Added to HUD
- **Bug fix**: Abandoned target word no longer persists when it falls off screen
- **38 unit tests** covering all game logic classes