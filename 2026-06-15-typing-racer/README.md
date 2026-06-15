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
- **Power-ups** appear periodically — they fall down and are collected when they reach near the bottom of the screen

When a word reaches the danger zone, you lose a life (♥). Lose all 5 lives and it's game over. Your score is saved to a persistent leaderboard.

## ✨ Features

### Core Gameplay
- **Progressive difficulty** — 4 word tiers unlock as you improve (easy, medium, hard, expert)
- **Smart targeting** — automatically locks onto the most urgent word matching your first keystroke
- **Combo system** — chain completions for score multipliers (each combo adds 0.25x)
- **Combo milestones** — visual 🔥 notification at every 5x combo streak
- **Target arrow** — ▼ indicator points at your currently targeted word

### Power-Ups
- **❄ Freeze** — freezes all falling words for 3 seconds, giving you time to catch up
- **💥 Bomb** — destroys all words on screen (resets your combo, does NOT count toward difficulty progression)
- **♥ +1 Life** — restores one life (up to a max of 5)

Power-ups spawn every 6–12 words and fall slowly down the screen. They are automatically collected when they reach near the bottom of the play area.

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
- **Pause screen** — press ESC to pause; shows current stats and allows Q to quit
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
- Terminal size at least 60×20 minimum (60×24 recommended)

## 🕹️ Controls

| Key | Action |
|-----|--------|
| `A-Z`, `a-z` | Type letters to destroy falling words |
| `ESC` | Pause / Resume |
| `Q` | Quit (from pause screen or game over screen) |
| `R` | Restart (on game over screen) |
| `Ctrl+C` | Force quit anytime |

## 📋 CLI Options

```bash
python3 typing_racer.py              # Start the game
python3 typing_racer.py --help       # Show help and usage info
python3 typing_racer.py --version    # Show version (2.1.0)
python3 typing_racer.py --scores     # Show high scores leaderboard
python3 typing_racer.py --reset      # Reset all high scores
```

## 📖 Gameplay Tips

1. **Prioritize low words** — the game auto-selects the word closest to the danger zone that matches your first keystroke
2. **Build combos** — consecutive completions give increasing score multipliers (each combo adds 0.25x, so a 5x combo = 2.0x multiplier)
3. **Watch for red words** — words in the danger zone glow red; focus on those first
4. **Expert words are worth 5x** — harder words give much more score, but are longer and faster
5. **Accuracy matters** — mistyped keys break your combo, so type carefully
6. **Grab power-ups** — Freeze is great for catching up, Bomb clears a crowded screen. Power-ups are collected automatically when they fall near the bottom
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

**Note:** Bomb power-up destroyed words give a flat +5 points each but do NOT count toward `words_completed`, so they won't artificially inflate your difficulty progression.

## 🧪 Testing

```bash
# Run all tests
python3 -m pytest test_typing_racer.py -v

# Or with unittest directly
python3 test_typing_racer.py
```

The test suite covers 52 tests including:
- `FallingWord` — initialization, typing, completion, freezing, edge cases
- `Particle` — physics, lifetime
- `PowerUp` — types, expiration, symbols, speed, unknown types
- `HighScoreManager` — add, save, load, sort, clear, corrupt-file handling, rank return values, field validation
- Word pool validation — lowercase, no duplicates, appropriate lengths, all alpha
- Scoring formula verification
- Version format check
- `TestBugFixes` — bomb words_completed, power-up collection, ESC during countdown, freeze effect, heart max lives, pause quit, spawn interval bounds

## 🏗️ Architecture

| Class | Purpose |
|-------|---------|
| `FallingWord` | A word falling down the screen with typing progress state |
| `Particle` | Simple physics particle for explosion effects |
| `PowerUp` | Collectible power-up (Freeze / Bomb / Heart) |
| `HighScoreManager` | JSON-based persistent leaderboard (top 10) |
| `TypingRacer` | Main game class — spawning, input, physics, rendering, game loop |

All rendering uses `curses` — no external UI library needed. The game loop uses delta-time updates (capped at 100ms) for consistent physics across different frame rates.

## 🐛 Bugs Fixed in v2.1

1. **Power-ups were never collected** — The `collect_powerup()` method existed but was never called from the game loop. Power-ups would fall and disappear without any effect. Now power-ups are automatically collected when they reach near the bottom of the screen (2 rows above the danger zone).
2. **Bomb power-up inflated difficulty progression** — Bombed words incorrectly incremented `words_completed`, causing premature level-ups and difficulty tier unlocks. Bombed words now only give a flat score bonus (+5 points each) and do NOT count toward difficulty progression.
3. **ESC during countdown started the game** — Pressing ESC during the 3-second countdown would immediately start the game instead of being ignored. ESC is now explicitly ignored during the countdown phase.
4. **No way to quit from pause** — Pressing Q during the pause screen had no effect. Now Q from the pause screen triggers game over (saves score) and allows clean exit.

## 🆕 What's New in v2.1

- **Fixed**: Power-ups are now actually collectible — they activate when they fall near the bottom of the screen
- **Fixed**: Bomb power-up no longer inflates difficulty progression
- **Fixed**: ESC key properly ignored during countdown (no longer accidentally starts the game)
- **Fixed**: Q key now works from the pause screen to quit (with score saving)
- **Added**: Pause screen now shows "Press Q to quit" hint
- **Added**: 14 new unit tests covering bug fixes and edge cases