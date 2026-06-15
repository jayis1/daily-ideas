# ⌨️ Terminal Typing Racer

A fast-paced typing game that runs entirely in your terminal. Words fall from the top of the screen — type them before they hit the danger zone! Features progressive difficulty, combo multipliers, particle explosions, and WPM tracking.

## 🎮 How It Works

Words appear at the top of the screen and fall downward. You type the words to destroy them before they reach the red danger zone at the bottom. As you complete words, the game gets harder:

- **New difficulty tiers unlock** as you complete more words (easy → medium → hard → expert)
- **Speed increases** with each level (every 8 words completed)
- **Spawn rate accelerates** the longer you survive
- **Combo system** rewards consecutive correct completions with score multipliers

When a word reaches the danger zone, you lose a life (♥). Lose all 5 lives and it's game over.

## ✨ Features

- **Progressive difficulty** — 4 word tiers unlock as you improve
- **Combo system** — chain completions for score multipliers (up to 5x+)
- **Particle explosions** — completed words burst into character particles with gravity
- **Real-time WPM** — tracks your words-per-minute as you play
- **Accuracy tracking** — shows your correct keystroke percentage
- **Danger zone** — words glow red as they approach the bottom
- **Smart targeting** — automatically locks onto the most urgent word matching your first keystroke
- **Pause support** — press ESC to pause/resume
- **Level flash** — visual notification when you level up or unlock a new tier

## 🚀 Installation

No external dependencies needed — uses only Python's standard library (`curses`).

```bash
# Clone and run
cd ~/daily-ideas/2026-06-15-typing-racer
python3 typing_racer.py
```

### Requirements

- Python 3.10+
- A terminal with color support (most modern terminals work)
- At least 80×24 terminal size recommended

## 🕹️ Controls

| Key | Action |
|-----|--------|
| `A-Z`, `a-z` | Type letters to destroy falling words |
| `ESC` | Pause / Resume |
| `R` | Restart (on game over screen) |
| `Q` | Quit (on game over screen) |
| `Ctrl+C` | Force quit anytime |

## 📖 Gameplay Tips

1. **Prioritize low words** — the game auto-selects the word closest to the danger zone that matches your first keystroke
2. **Build combos** — consecutive completions give increasing score multipliers (each combo adds 0.25x)
3. **Watch for red words** — words in the danger zone glow red; focus on those first
4. **Expert words are worth 5x** — harder words give much more score, but are longer and faster
5. **Accuracy matters** — mistyped keys break your combo, so type carefully

## 📊 Scoring

```
Points = (10 + word_length) × combo_multiplier × difficulty_bonus
```

| Difficulty | Bonus |
|-----------|-------|
| Easy      | 1x    |
| Medium    | 2x    |
| Hard      | 3x    |
| Expert    | 5x    |

## 🏗️ Architecture

- **`FallingWord`** — represents a falling word with typing state tracking
- **`Particle`** — simple physics particle for explosion effects
- **`TypingRacer`** — main game class handling spawning, input, physics, and rendering
- All rendering uses `curses` — no external UI library needed