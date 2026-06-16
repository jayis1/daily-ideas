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
- **Case-insensitive input** — Caps Lock won't break your game; uppercase and lowercase both work
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
- **Combo + unlock combined notifications** — when a combo milestone coincides with a difficulty unlock, both are displayed together

### Meta Features
- **Persistent high scores** — top 10 scores saved to `.typing_racer_scores.json`
- **Score saved immediately on game over** — your score is recorded as soon as the game ends, so it's preserved even if you restart or quit
- **3-second countdown** — gives you time to get ready before words start falling (press any key to skip, with a brief delay before the first word)
- **Pause screen** — press ESC to pause; shows current stats and allows Q to quit
- **Terminal resize handling** — adapts if you resize your terminal mid-game
- **Minimum size check** — warns if your terminal is too small (needs 60×20 minimum)
- **Non-letter key filtering** — pressing space, digits, or punctuation won't affect your combo or accuracy
- **Q key safety** — pressing Q during active gameplay is ignored (it's only active during pause and game-over screens)

## 🚀 Installation

No external dependencies — uses only Python's standard library (`curses`, `json`, `argparse`, `math`).

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
| `A-Z`, `a-z` | Type letters to destroy falling words (case-insensitive; Q is excluded during active play) |
| `ESC` | Pause / Resume |
| `Q` | Quit (from pause screen or game over screen only — ignored during active gameplay) |
| `R` | Restart (on game over screen) |
| `Ctrl+C` | Force quit anytime |

**Note:** Non-letter keys (space, digits, punctuation) and the Q key are silently ignored during active gameplay and won't affect your combo or accuracy.

## 📋 CLI Options

```bash
python3 typing_racer.py              # Start the game
python3 typing_racer.py --help       # Show help and usage info
python3 typing_racer.py --version    # Show version (2.4.0)
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
8. **Caps Lock is fine** — the game converts all letter input to lowercase, so Caps Lock won't hurt you
9. **Don't worry about Q** — pressing Q during gameplay is ignored, it only works as a quit key from the pause or game-over screens

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

The test suite covers 69 tests including:
- `FallingWord` — initialization, typing, completion, freezing, edge cases, empty word guard
- `Particle` — physics, lifetime
- `PowerUp` — types, expiration, symbols, speed, unknown types
- `HighScoreManager` — add, save, load, sort, clear, corrupt-file handling, entry validation, rank return values, field validation
- Word pool validation — lowercase, no duplicates, appropriate lengths, all alpha
- Scoring formula verification
- Version format check
- `TestBugFixes` — v2.1: bomb words_completed, power-up collection, ESC during countdown, freeze effect, heart max lives, pause quit, spawn interval bounds; v2.2: case-insensitive matching, non-alpha key filtering, score entry validation, unlocked tier weight guarantee; v2.3: Q key ignored during gameplay, countdown display fix, power-up spawn interval fix, score saved on game-over, score save idempotency; v2.4: lives clamped to 0, game-over triggers only once per frame, spawn_timer set on countdown skip, empty word guard, notification append for combo+unlock, lives display clamped

## 🏗️ Architecture

| Class | Purpose |
|-------|---------|
| `FallingWord` | A word falling down the screen with typing progress state |
| `Particle` | Simple physics particle for explosion effects |
| `PowerUp` | Collectible power-up (Freeze / Bomb / Heart) |
| `HighScoreManager` | JSON-based persistent leaderboard (top 10) |
| `TypingRacer` | Main game class — spawning, input, physics, rendering, game loop |

All rendering uses `curses` — no external UI library needed. The game loop uses delta-time updates (capped at 100ms) for consistent physics across different frame rates.

## 🐛 Bugs Fixed

### v2.4
1. **Lives could go negative** — When multiple words fell past the danger zone in the same frame, each one decremented `lives` by 1, causing lives to drop below 0 (e.g., 5 words hitting bottom at once from 2 lives would leave lives at -3). The lives counter is now clamped to 0 and the game-over check is gated so it only triggers once per frame. The HUD and pause screen also clamp lives to the 0–5 range for display.
2. **No delay when skipping countdown** — When the player pressed a key to skip the 3-second countdown, `spawn_timer` remained at 0.0 (its initial value), causing the first word to spawn immediately with no grace period. Now `spawn_timer` is set to 0.5 when the countdown is skipped, matching the delay that occurs when the countdown expires naturally.
3. **Empty word gave free points** — Completing a `FallingWord` with an empty string awarded 10 base points and incremented `words_completed`. While empty words shouldn't normally appear in gameplay, `_complete_word` now has an early-return guard that prevents scoring, combo increment, or progression for empty words.
4. **Difficulty unlock overwrote combo milestone** — When a combo milestone (5x, 10x, etc.) coincided with a difficulty tier unlock in the same frame, the unlock notification replaced the combo milestone text. Now the unlock text is appended to any existing milestone notification (e.g., "🔥 5x COMBO!  |  UNLOCKED: MEDIUM") so both messages are visible.
5. **Lives display showed wrong number of hearts** — When `lives` went negative (see bug #1), the HUD showed 6+ empty hearts instead of exactly 5. The display now uses `max(0, min(5, lives))` to always render exactly 5 heart slots.

### v2.3
1. **Score lost on restart** — Pressing R to restart after game over would clear all game state (including `words_completed`) before the score could be saved. The score is now saved immediately when game over first occurs via `_save_score()`, which uses an idempotent `score_saved` flag to prevent double-saving. The `reset()` method properly resets this flag for the next game.
2. **Q key resets combo during active gameplay** — Pressing Q during active (non-paused, non-game-over) gameplay was treated as a regular letter input. Since words like "quest" and "quintessence" start with Q, this could accidentally target them, and if no Q-word existed, it would reset your combo. Q is now silently ignored during active gameplay and only functions as a quit key from pause/game-over screens.
3. **Countdown timer off-by-one** — The 3-second countdown displayed the wrong number at integer boundaries. At `countdown=2.0`, it showed "3" instead of "2"; at `countdown=1.0`, it showed "2" instead of "1". Fixed by replacing `int(countdown)+1` with `math.ceil(countdown)`.
4. **Power-up spawn interval re-rolled every word** — `maybe_spawn_powerup()` generated a new random interval (6–12) on every call, meaning the counter could hit a freshly rolled low number on any word. This made power-ups spawn much more frequently than intended. The target interval is now stored in `powerup_spawn_target` and only re-rolled after a power-up actually spawns.

### v2.2
1. **Case sensitivity broke gameplay** — Uppercase letters (e.g., from Caps Lock) didn't match lowercase words, causing the combo to reset. Input is now converted to lowercase before matching.
2. **Non-letter keys reset combo** — Pressing space, digits, or punctuation while targeting a word would trigger the wrong-character path and reset the combo. Non-alphabetic keys are now silently ignored.
3. **HighScoreManager crashed on corrupt entries** — Loading a score file containing non-dict entries caused crashes. Entries are now validated on load.
4. **Unlocked difficulty tiers had zero spawn weight** — When hard/expert tiers were unlocked, their spawn weight was 0 until higher levels. All unlocked tiers now have a minimum weight of 1.

### v2.1
1. **Power-ups were never collected** — The `collect_powerup()` method existed but was never called from the game loop. Now collected automatically when near the bottom.
2. **Bomb power-up inflated difficulty progression** — Bombed words incorrectly incremented `words_completed`. Now they only give a flat +5 score bonus.
3. **ESC during countdown started the game** — ESC is now explicitly ignored during the countdown phase.
4. **No way to quit from pause** — Q during pause now triggers game over with score saving.