# Terminal Séance — Ouija Board Simulator

🕯️ Conduct a séance right in your terminal. Place your fingers on the planchette, ask the spirits a question, and watch as the planchette glides across an ANSI-rendered Ouija board, spelling out messages from beyond the veil.

![Terminal Séance](https://img.shields.io/badge/theme-supernatural-purple) ![Python](https://img.shields.io/badge/python-3.8+-blue) ![No Dependencies](https://img.shields.io/badge/dependencies-zero-success) ![Version](https://img.shields.io/badge/version-1.1.1-orange)

---

## ✟ What It Does

Terminal Séance is an interactive, animated Ouija board simulator. When you start the program:

1. **A spirit is summoned** — one of eight unique ghostly personalities materializes, each with its own speaking style, vocabulary, color theme, and backstory.
2. **The board appears** — a full ANSI-art Ouija board renders in your terminal, complete with letters A–Z in two arcs, numbers 0–9, YES/NO markers, a sun, a moon, decorative stars, and a GOODBYE at the bottom.
3. **You ask a question** — type any question and press ENTER.
4. **The planchette moves** — a heart-shaped planchette with a glowing peephole (◉) smoothly glides from letter to letter with organic easing and a supernatural wobble, leaving a faint trail behind it.
5. **The message is revealed** — the spirit spells out its response, which could be letters, numbers, YES/NO, or a dramatic GOODBYE.

## 👻 The Spirits

Eight spirits haunt this board, each with a distinct personality:

| Spirit | Style | YES-bias | Description |
|--------|-------|----------|-------------|
| **The Whisperer** | cryptic | 35% | A faint, sorrowful presence |
| **Captain Aldous** | nautical | 50% | An old sea captain lost in 1887 |
| **Little Rose** | childish | 60% | A child who never grew up |
| **The Mathematician** | precise | 45% | A scholar obsessed with prime numbers |
| **The Jester** | mischievous | 55% | A trickster who never tells a straight answer |
| **The Prophet** | prophetic | 50% | A seer who speaks only of what is to come |
| **The Inventor** | mechanical | 48% | A Victorian tinkerer trapped between gears |
| **The Mourner** | sorrowful | 30% | A widow in perpetual grief, endlessly waiting |

Each spirit has its own vocabulary, color, yes/no bias, and farewell word. Press **`r`** mid-séance to dismiss the current spirit and summon a new one, or use `--spirit NAME` to choose one at launch.

List all spirits without starting a session:

```bash
python3 ouija.py --list-spirits
```

## 🎮 Controls

| Key | Action |
|-----|--------|
| `ENTER` | Ask a question / submit |
| `r` | Dismiss current spirit, summon a new one |
| `s` | Save session transcript (requires `--log`) |
| `h` | Show in-séance help |
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
# Normal interactive séance
python3 ouija.py

# Slow, dramatic planchette movement
python3 ouija.py --slow

# Fast planchette (impatient mode)
python3 ouija.py --fast

# Summon a specific spirit by name
python3 ouija.py --spirit "Captain Aldous"

# Disable ANSI colors (accessibility / pipe-friendly)
python3 ouija.py --no-color

# Save session Q&A to a Markdown log file
python3 ouija.py --log seance-log.md

# Reproducible séance with a fixed random seed
python3 ouija.py --seed 42

# Non-interactive demo mode (cycles through all spirits, no TTY needed)
python3 ouija.py --demo

# Show version
python3 ouija.py --version

# List all available spirits
python3 ouija.py --list-spirits

# Show help
python3 ouija.py --help
```

**Note:** `--slow` and `--fast` are mutually exclusive. Using both together will produce an error regardless of which mode you're running.

## 💬 Usage Examples

### Interactive Session

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

### Demo Mode Output

```bash
python3 ouija.py --demo --fast --no-color
```

Cycles through every spirit non-interactively — great for screenshots or environments without a TTY:

```
  ☽  The Whisperer
       a faint, sorrowful presence
  Q: Is anyone there?
  A: [NO]

  ☽  Captain Aldous
       an old sea captain lost in 1887
  Q: What is your name?
  A: COMPASS
  ...
```

### Session Logging

```bash
python3 ouija.py --log seance-log.md
```

Each Q&A exchange is appended to the log file in Markdown format:

```markdown
# Terminal Séance — Session Log
# Created 2026-07-29T12:00:00

## 2026-07-29T12:01:30 — The Whisperer
**Q:** Is anyone there?
**A:** [YES] WAITING

## 2026-07-29T12:02:15 — The Whisperer
**Q:** What do you want?
**A:** REMEMBER
```

At the end of the session a summary is printed listing every exchange.

### Running the Tests

```bash
python3 test_seance.py
```

The test suite (20 tests) verifies:

- All 26 letters + 10 digits have valid board positions
- All 8 spirits are well-formed with required fields
- Response generation produces valid tokens for every spirit across multiple questions
- Target positions are valid for all letters, numbers, and special tokens (YES/NO/GOODBYE)
- The easing function is monotonic, bounded, and clamped
- The board renders with all letters, numbers, and special words
- The planchette shape includes the peephole (◉) and pointer (V)
- `--no-color` mode strips all ANSI escape codes
- Spirit lookup by name works (case-insensitive, validation, exclusion)
- `tokens_to_string()` renders readable messages
- `SessionLog` writes a Markdown transcript correctly
- The YN_WORDS set is well-formed
- The version string is valid semver
- Demo mode runs without errors and covers all spirits
- Seeded random produces reproducible responses
- `generate_response` handles None and non-string questions without crashing
- `SessionLog` handles nonexistent directory paths gracefully
- The board title line aligns with the border lines
- `--slow` and `--fast` mutual exclusion is enforced even with `--demo`

## 🔮 Features

### Core
- **8 unique spirit personalities** with distinct vocabularies, colors, and response styles
- **Smooth animated planchette** with smoothstep easing and supernatural wobble effect
- **Faint trail** that follows the planchette as it moves, fading over time
- **Full Ouija board** with arched letter layout, numbers, YES/NO, GOODBYE, sun, moon, and stars
- **Question-aware responses** — yes/no questions get YES/NO answers more often; open questions get spelled-out words
- **Atmospheric ANSI styling** — each spirit has its own color theme

### CLI flags
- `--version` — print version and exit
- `--list-spirits` — print a formatted table of all spirits and exit
- `--spirit NAME` — summon a specific spirit by name (case-insensitive)
- `--no-color` — disable ANSI colors (accessibility / pipe-friendly)
- `--slow` / `--fast` — control planchette speed (mutually exclusive)
- `--log FILE` — append session Q&A to FILE (Markdown)
- `--demo` — non-interactive auto-séance (cycles through spirits, no TTY needed)
- `--seed N` — deterministic random seed for reproducible séances
- `--help` — show help

### In-séance commands
- `r` — re-roll the spirit (new personality)
- `q` — quit the séance
- `h` — show help / controls
- `s` — save session transcript

## 🛠️ Technical Details

- **Easing**: The planchette uses a smoothstep easing function (`3t² - 2t³`) for organic acceleration/deceleration, with input clamping for safety
- **Wobble**: A sinusoidal perturbation gives the planchette an unsettling, supernatural movement quality
- **Board rendering**: The board is rendered into a 2D character grid, then overlaid with the planchette using ANSI cursor positioning
- **Response generation**: Each spirit draws from its vocabulary to construct 1–3 word responses, with a chance of YES/NO for yes/no questions and a small chance of GOODBYE
- **Color handling**: A global `_c()` helper strips ANSI codes when `--no-color` is active, making output safe for pipes and accessible terminals
- **Session logging**: A `SessionLog` class appends each exchange to a Markdown file with timestamps, and prints a summary at session end
- **Non-TTY safety**: `clear_screen()` detects whether stdout is a TTY and falls back to a newline separator in piped/CI environments

## 📁 Files

| File | Description |
|------|-------------|
| `ouija.py` | Main program — the séance simulator (CLI + interactive + demo modes) |
| `test_seance.py` | 20-test suite covering core logic, new features, and bug fixes |
| `render_demo.py` | Renders a static board frame for screenshots (supports `--no-color`) |

## 📋 Changelog

### v1.1.1 — Bug fixes
- **Fixed board title misalignment**: The "THE SPIRIT BOARD" title line was 2 characters narrower than the border lines (missing the `"  "` prefix), causing visual misalignment. Now properly aligned.
- **Fixed `generate_response` crash on None/non-string input**: Passing `None` or a non-string (e.g., `int`) as the question caused an `AttributeError` on `.lower()`. Now coerces non-string input to an empty string, which produces a cryptic default response.
- **Fixed `SessionLog` crash on nonexistent directory**: Providing `--log /nonexistent/dir/file.md` caused an unhandled `FileNotFoundError` that crashed the program. Now catches `OSError`, prints a warning, and disables logging so the séance can continue.
- **Fixed `--slow --fast` mutual exclusion bypass**: The validation was placed after the `--demo` and `--list-spirits` dispatch, so `--demo --slow --fast` would silently run demo mode instead of erroring. Now validated before any mode dispatch.
- **Fixed unprotected `input()` calls**: Three `input()` calls (after `print_intro`, in the `r` re-roll command, and in the `h` help command) were not wrapped in `EOFError`/`KeyboardInterrupt` handlers, causing crashes when stdin was closed (e.g., piped input, Ctrl+D). All now handled gracefully.
- **Fixed misleading `'s'` save command**: The save command claimed "Session log saved" but didn't actually write anything new — the log is already written incrementally. Now appends a timestamped save marker to the log file and reports the actual path from `session_log.path` (which may differ from `args.log` if logging was disabled).
- **Fixed `SessionLog.add()` write error handling**: If the log file became unwritable mid-session (e.g., disk full, permissions changed), `add()` would crash. Now catches `OSError`, prints a warning, and disables further logging attempts.
- **Fixed `clear_screen` in non-TTY environments**: `os.system("clear")` printed "TERM environment variable not set" when stdout was piped. Now detects TTY status and falls back to a newline separator.
- **Added 5 new tests** (15 → 20) covering all bug fixes: None/non-string question handling, bad log path, title alignment, and slow/fast mutual exclusion.
- **Version bumped** from 1.1.0 to 1.1.1.

### v1.1.0 — Feature enhancements
- 2 new spirits (The Inventor, The Mourner)
- `--spirit NAME`, `--list-spirits`, `--no-color`, `--log FILE`, `--demo`, `--seed N`, `--fast` flags
- `--version` and `--help` with epilog
- In-séance `h` (help) and `s` (save log) commands
- Terminal size detection with warnings
- Easing function clamping, empty-question support, unknown-token fallback
- Expanded test suite (7 → 15)
- Zero dependencies — pure Python standard library

### v1.0.0 — Initial release
- 6 spirits with distinct personalities
- Animated planchette with easing and wobble
- Full Ouija board rendering (letters, numbers, YES/NO/GOODBYE, sun, moon, stars)
- Interactive séance loop with re-roll, quit controls
- 7-test suite

---

*"The candles are extinguished. The séance has ended. The spirits rest. Until next time... ✟"*