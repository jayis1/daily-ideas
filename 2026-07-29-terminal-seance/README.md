# Terminal Séance — Ouija Board Simulator

🕯️ Conduct a séance right in your terminal. Place your fingers on the planchette, ask the spirits a question, and watch as the planchette glides across an ANSI-rendered Ouija board, spelling out messages from beyond the veil.

![Terminal Séance](https://img.shields.io/badge/theme-supernatural-purple) ![Python](https://img.shields.io/badge/python-3.8+-blue) ![No Dependencies](https://img.shields.io/badge/dependencies-zero-success)

---

## ✟ What It Does

Terminal Séance is an interactive, animated Ouija board simulator. When you start the program:

1. **A spirit is summoned** — one of six unique ghostly personalities materializes, each with their own speaking style, vocabulary, color theme, and backstory.
2. **The board appears** — a full ANSI-art Ouija board renders in your terminal, complete with letters A–Z in two arcs, numbers 0–9, YES/NO markers, a sun, a moon, decorative stars, and a GOODBYE at the bottom.
3. **You ask a question** — type any question and press ENTER.
4. **The planchette moves** — a heart-shaped planchette with a glowing peephole (◉) smoothly glides from letter to letter with organic easing and a supernatural wobble, leaving a faint trail behind it.
5. **The message is revealed** — the spirit spells out its response, which could be letters, numbers, YES/NO, or a dramatic GOODBYE.

## 👻 The Spirits

| Spirit | Description | Style |
|--------|-------------|-------|
| **The Whisperer** | A faint, sorrowful presence | Cryptic, speaks of shadows and forgotten things |
| **Captain Aldous** | An old sea captain lost in 1887 | Nautical, speaks of storms and the deep |
| **Little Rose** | A child who never grew up | Childish, wants to play hide and seek |
| **The Mathematician** | A scholar obsessed with primes | Precise, spells out numbers and sequences |
| **The Jester** | A trickster who never answers straight | Mischievous, says "maybe" and "perhaps" |
| **The Prophet** | A seer who speaks only of what is to come | Prophetic, warns of fire and change |

Each spirit has its own vocabulary, color, yes/no bias, and farewell word. Press **`r`** mid-séance to dismiss the current spirit and summon a new one.

## 🎮 Controls

| Key | Action |
|-----|--------|
| `ENTER` | Ask a question / submit |
| `r` | Dismiss current spirit, summon a new one |
| `q` | End the séance and exit |
| `Ctrl+C` | Quit immediately |

## 📦 Installation

No dependencies required — just Python 3.8+.

```bash
# Clone or download this folder
cd 2026-07-29-terminal-seance

# Make executable (optional)
chmod +x ouija.py

# Run
python3 ouija.py
```

## ▶️ How to Run

```bash
# Normal speed
python3 ouija.py

# Slow, dramatic planchette movement
python3 ouija.py --slow
```

## 💬 Usage Examples

### Example Session

```
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ✟  TERMINAL SÉANCE  ✟
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  The candles flicker. The room grows cold...
  A presence makes itself known:

  ☽  The Whisperer
     a faint, sorrowful presence

  Place your fingers on the planchette.
  Ask your question, then press ENTER...
```

You type: `Is anyone there?`

The planchette glides to **Y** → **E** → **S**, then drifts to the **YES** corner. The spirit spells: `[YES] SHADOWS`

You type: `What do you want?`

The planchette moves to **R** → **E** → **M** → **E** → **M** → **B** → **E** → **R**, pausing at each letter. The spirit spells: `REMEMBER`

Finally, the planchette slides to **GOODBYE** and the séance ends for that question.

### Running the Tests

```bash
python3 test_seance.py
```

Verifies that all 26 letters + 10 digits have valid board positions, all 6 spirits produce valid responses, the easing function is monotonic, the board renders correctly, and the planchette shape includes its peephole and pointer.

## 🔮 Features

- **6 unique spirit personalities** with distinct vocabularies, colors, and response styles
- **Smooth animated planchette** with easing function and supernatural wobble effect
- **Faint trail** that follows the planchette as it moves, fading over time
- **Full Ouija board** with arched letter layout, numbers, YES/NO, GOODBYE, sun, moon, and stars
- **Question-aware responses** — yes/no questions get YES/NO answers more often; open questions get spelled-out words
- **Atmospheric ANSI styling** — each spirit has its own color theme
- **Zero dependencies** — pure Python standard library
- **`--slow` mode** for extra dramatic séances

## 🛠️ Technical Details

- **Easing**: The planchette uses a smoothstep easing function (`3t² - 2t³`) for organic acceleration/deceleration
- **Wobble**: A sinusoidal perturbation gives the planchette an unsettling, supernatural movement quality
- **Board rendering**: The board is rendered into a 2D character grid, then overlaid with the planchette using ANSI cursor positioning
- **Response generation**: Each spirit draws from its vocabulary to construct 1–3 word responses, with a chance of YES/NO for yes/no questions and a small chance of GOODBYE

## 📁 Files

| File | Description |
|------|-------------|
| `ouija.py` | Main program — the séance simulator |
| `test_seance.py` | Smoke tests for core logic |
| `render_demo.py` | Renders a static board frame for screenshots |

---

*"The candles are extinguished. The séance has ended. The spirits rest. Until next time... ✟"*