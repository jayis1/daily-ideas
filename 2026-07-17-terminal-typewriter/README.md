# ⌨ Terminal Typewriter Simulator

**v1.3.0**

A fully interactive vintage typewriter simulator that runs right in your terminal. Experience the feel of typing on classic machines — from the satisfying clack of an Underwood No. 5 to the precision of an Olivetti Lettera 32 — complete with ink density variation, ribbon wear, paper jams, the iconic margin bell, deterministic playback, auto-wrap, session statistics, and more.

## Features

### Typewriter Models
- **Underwood No. 5** — the classic workhorse with heavy, satisfying keystrokes
- **Remington Portable** — light and quick
- **Olivetti Lettera 32** — Italian design, smooth and precise
- **IBM Selectric II** — the electric revolution, fast and consistent
- **Royal Quiet De Luxe** — elegant but temperamental, with moody ink

### Simulation Mechanics
- **Ink Density Simulation** — characters vary in darkness based on ribbon wear and random variation, just like a real typewriter
- **Ribbon Wear** — the longer you type, the fainter the ink gets. Install a fresh ribbon with `Ctrl+N`
- **Margin Bell** — hear the classic "ding" when approaching the right margin
- **Overstrike Corrections** — press Backspace to overprint corrections (marked with ⌫)
- **Paper Jams** — random jam events that block typing until you clear them with `Ctrl+J` (jam frequency varies by model — the Royal jams most, the IBM Selectric almost never). During auto-type, jams automatically pause playback and resume when cleared.
- **CAPS LOCK Toggle** — `Ctrl+C` toggles caps lock
- **Timestamp Stamping** — `Ctrl+T` inserts the current date and time (disabled while jammed)
- **Speed Control** — adjust auto-type playback speed from 0.1x to 10x with `--speed`
- **Export to File** — save your typed work to a file with `--export`; press `Ctrl+E` mid-session to save with visual confirmation
- **Word & Character Count** — live word count in the status bar
- **Auto-Type Mode** — feed text from the command line or a file and watch it type itself; auto-pauses on paper jams
- **Ink Colors** — choose black, red, blue, or green ink
- **Beautiful Paper Rendering** — your text appears on a white "page" with margins and a roller bar
- **Visual Flash Feedback** — export actions show on-screen confirmation messages

### New in v1.3.0
- **Deterministic Mode (`--seed N`)** — seed the random number generator so ink variation, typing delays, and jam rolls are reproducible run-to-run. Great for demos, testing, and scripting.
- **Auto-Wrap at Margin (`--wrap`)** — when enabled, the carriage automatically returns to the next line once you pass the margin, just like a real typewriter whose carriage hit the right stop. No more running off the page.
- **Hide Header (`--no-header`)** — suppress the status/controls banner for a clean, distraction-free writing surface.
- **Runtime Sound Toggle (`Ctrl+S`)** — turn the bell on or off mid-session without restarting. The status bar shows the current sound state.
- **Tab Key Support** — pressing Tab in interactive mode inserts 4 spaces, like setting a tab stop on a real machine.
- **Session Statistics (`--stats FILE`)** — on quit, writes a human-readable summary (characters, words, lines, ribbon wear, duration, chars/sec) to a file.
- **Terminal Size Guard** — if the terminal is too small (under 50×12), a friendly message is shown instead of a garbled display.
- **Seeded Demo Mode** — `--demo --seed N` produces identical output every time, handy for screenshots and regression checks.

## Installation

No external dependencies required — uses only Python's standard library (`curses`, `random`, `time`, `argparse`).

```bash
cd daily-ideas/2026-07-17-terminal-typewriter/

# Make executable (optional)
chmod +x typewriter.py
```

**Requirements:** Python 3.6+ and a terminal with curses support (most Linux/macOS terminals). For the best experience, use a terminal that supports colors and the terminal bell, with a size of at least 50 columns × 12 rows.

## How to Run

### Interactive Mode (default)

```bash
python3 typewriter.py
```

Starts the full interactive typewriter. Type anything and watch it appear on the paper!

### Choose a Typewriter Model

```bash
python3 typewriter.py --model royal
python3 typewriter.py -m ibm
```

Options: `underwood` (default), `remington`, `olivetti`, `ibm`, `royal`

### Choose Ink Color

```bash
python3 typewriter.py --color red
python3 typewriter.py -m olivetti -c blue
```

Options: `black` (default), `red`, `blue`, `green`

### Auto-Type from Command Line

```bash
python3 typewriter.py -t "The quick brown fox jumps over the lazy dog."
```

### Auto-Type from a File

```bash
python3 typewriter.py -f sample_letter.txt
```

### Auto-Type with Speed Control

```bash
# Type at 3x speed
python3 typewriter.py -t "Fast typist here" -s 3.0

# Slow, deliberate typing at 0.5x speed
python3 typewriter.py -f poem.txt -s 0.5
```

Speed range: 0.1 (very slow) to 10.0 (very fast), default is 1.0.

### Auto-Wrap at Margin

```bash
# The carriage returns automatically when you reach the margin
python3 typewriter.py --wrap
python3 typewriter.py --wrap -t "A very long line that would normally run past the right margin and disappear."
```

### Deterministic / Reproducible Mode

```bash
# Same seed → same ink variation, delays, and jam rolls every time
python3 typewriter.py --seed 42
python3 typewriter.py --seed 42 -t "Reproducible typing demo"
```

### Export Typed Content to File

```bash
# Everything you type will be saved to output.txt when you quit
python3 typewriter.py --export my_letter.txt

# Combine with auto-type for conversion
python3 typewriter.py -f input.txt --export output.txt -s 5.0
```

### Write Session Statistics

```bash
# On quit, writes character/word/line counts and timing to stats.txt
python3 typewriter.py --stats session_stats.txt
python3 typewriter.py -f sample_letter.txt --stats stats.txt --export out.txt
```

Example `stats.txt` content:
```
Typewriter: Underwood No. 5
Characters: 138
Words: 22
Lines: 7
Ribbon wear: 2.8%
Session duration: 12.4s
Characters/sec: 11.13
```

### Hide the Header

```bash
# Clean, distraction-free writing surface — no status bar or controls banner
python3 typewriter.py --no-header
```

### Demo Mode (non-interactive)

```bash
python3 typewriter.py --demo

# Seeded demo for reproducible output
python3 typewriter.py --demo --seed 42
```

Prints a static typewriter-styled demo to stdout (no curses required).

### Disable Bell

```bash
python3 typewriter.py --quiet
```

You can also toggle the bell at runtime with `Ctrl+S`.

### Show Version

```bash
python3 typewriter.py --version
# Output: Terminal Typewriter Simulator v1.3.0
```

### Show Help

```bash
python3 typewriter.py --help
```

## Interactive Controls

| Key | Action |
|-----|--------|
| **Any printable key** | Type that character |
| **Tab** | Insert 4 spaces (indent) |
| **Enter** | Carriage return + line feed |
| **Ctrl+J** | Clear paper jam (when jammed) / Line Feed (when not jammed) |
| **Backspace** | Overstrike last character (correction) |
| **Ctrl+U** | New line |
| **Ctrl+R** | Carriage return (no line feed) |
| **Ctrl+D** | Ring the bell manually |
| **Ctrl+S** | Toggle bell sound on/off |
| **Ctrl+N** | Install a fresh ribbon (reset ink density) |
| **Ctrl+P** | Pause/resume auto-type |
| **Ctrl+C** | Toggle CAPS LOCK |
| **Ctrl+T** | Insert timestamp (date + time) |
| **Ctrl+E** | Export to file (if `--export` set); shows on-screen confirmation |
| **Q** | Quit (auto-exports if `--export` is set; writes stats if `--stats` is set) |

## Usage Examples

### Compose a letter on the Royal Quiet De Luxe

```bash
python3 typewriter.py -m royal
```

### Auto-type a file with blue ink on the Olivetti at double speed

```bash
python3 typewriter.py -m olivetti -c blue -f my_poem.txt -s 2.0
```

### Type interactively and save to a file

```bash
python3 typewriter.py --export my_document.txt
```

### Distraction-free writing with auto-wrap and stats

```bash
python3 typewriter.py --no-header --wrap --export novel.txt --stats novel_stats.txt
```

### Reproducible demo for a screenshot

```bash
python3 typewriter.py --demo --seed 42
```

Output:
```
  ╔════════════════════════════════════════════════════════════════════╗
  ║  ⌨                         Underwood No. 5                          ║
  ╚════════════════════════════════════════════════════════════════════╝

  ┌────────────────────────────────────────────────────────────────────┐
  │ The quick brown fox jumps over the lazy dog.                        │
  │ Every letter of the alphabet, typed with care.                      │
  │ A typewriter is a mechanical marvel!                                │
  │ DING! The margin bell rings.                                        │
  └────────────────────────────────────────────────────────────────────┘

  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
```

## How It Works

The simulator models several aspects of a real typewriter:

1. **Keystroke Timing** — Each model has different min/max delay ranges. The Underwood No. 5 has heavy, slow keys (0.03–0.09s), while the IBM Selectric II is fast and electric (0.015–0.05s). Random variation simulates human typing, with occasional longer pauses for finger repositioning. The `--speed` flag multiplies playback speed.

2. **Ink Density** — Every character's ink density is calculated from the ribbon's wear level plus a Gaussian random variable. Fresh ribbons produce bold, dark text; worn ribbons produce faint, uneven impressions. The ink variance parameter differs per model — the Royal has high variance (moody ink), the IBM has low variance (consistent).

3. **Ribbon Wear** — The ribbon degrades slowly with each character typed (0.02% per character). After ~5000 characters, text starts getting noticeably fainter. Press `Ctrl+N` to install a fresh ribbon.

4. **Margin Bell** — Each model has a different "ding at" column (where the bell rings to warn you about the right margin). The Underwood dings at column 65, the IBM at 75. This matches the physical margin settings of each machine.

5. **Paper Jams** — Each model has a per-character chance of jamming. The Royal (temperamental!) has the highest jam rate at 0.4%, while the IBM Selectric (electric and reliable) has the lowest at 0.03%. When jammed, no characters can be typed until you clear it with `Ctrl+J`, which produces a satisfying bell acknowledgment. In auto-type mode, jams automatically pause playback, and clearing the jam auto-resumes.

6. **Overstrike Corrections** — Rather than erasing, backspace overstrikes with a ⌫ character, mimicking how real typists corrected mistakes by typing X over the error.

7. **Timestamps** — Press `Ctrl+T` to insert a `--- YYYY-MM-DD HH:MM ---` timestamp line, just like stamping a date on a letter. Disabled while jammed (the typewriter can't type through a jam).

8. **Export** — When `--export FILE` is set, your typed content is automatically saved to that file when you quit. You can also press `Ctrl+E` to save mid-session, which shows a visual "Exported!" or "Export failed!" confirmation on screen.

9. **Auto-Wrap** — With `--wrap`, once the carriage passes the margin (`ding_at + 5` columns), a carriage return + line feed is automatically performed. This mirrors a real typewriter where the carriage physically can't go further right — the typist must return it.

10. **Deterministic Mode** — With `--seed N`, all random calls (typing delays, ink density variation, jam probability rolls) draw from a seeded `random.Random` instance instead of the global RNG. Two runs with the same seed and same input produce identical results — essential for reproducible demos, regression testing, and scripting.

11. **Session Statistics** — With `--stats FILE`, the simulator records the model name, total characters, word count, line count, ribbon wear percentage, session duration, and characters-per-second rate, written to the file on quit. Useful for tracking writing sessions.

12. **Escape Sequence Handling** — Terminal escape sequences (arrow keys, function keys, etc.) are properly drained using CSI final byte detection (0x40–0x7E), preventing stray characters from appearing on the page.

## Testing

Run the test suite with pytest:

```bash
python3 -m pytest test_typewriter.py -v
```

The test suite covers:
- State initialization and configuration
- All model properties (delays, ink variance, jam chance)
- Model name verification
- Version format validation
- Demo function output for all models
- Ribbon wear mechanics
- Text reconstruction and word counting
- Caps lock behavior
- Export path handling
- Paper jam state mechanics
- Ctrl+J / Enter keycode conflict verification
- Auto-type jam auto-pause behavior
- Timestamp insertion while jammed
- Export feedback (success and failure paths)
- Escape sequence CSI byte range validation
- **Deterministic seed reproducibility** (v1.3.0)
- **Stats file output** (v1.3.0)
- **Auto-wrap at margin** (v1.3.0)
- **Terminal size guard constants** (v1.3.0)
- **New keycodes (Tab, Ctrl+S)** (v1.3.0)
- **Seeded demo mode** (v1.3.0)

**79 tests total.**

## Files

| File | Description |
|------|-------------|
| `typewriter.py` | Main application (interactive + demo modes) |
| `test_typewriter.py` | Comprehensive unit tests (79 tests) |
| `test_demo.py` | Demo script showing all 5 typewriter models |
| `sample_letter.txt` | Sample text file for auto-type testing |

## Changelog

### v1.3.0 (Enhancement)
- **New: `--seed N` deterministic mode** — ink variation, typing delays, and jam rolls become reproducible run-to-run via a seeded RNG.
- **New: `--wrap` auto-wrap at margin** — the carriage automatically returns once you pass the margin, like a real typewriter.
- **New: `--no-header`** — hide the status/controls banner for distraction-free writing.
- **New: `Ctrl+S` runtime sound toggle** — turn the bell on/off mid-session; status bar reflects the current state.
- **New: Tab key support** — inserts 4 spaces in interactive mode.
- **New: `--stats FILE`** — writes session statistics (chars, words, lines, ribbon wear, duration, chars/sec) on quit.
- **New: terminal size guard** — friendly message if terminal is under 50×12 instead of a garbled display.
- **New: seeded demo mode** — `--demo --seed N` produces identical output every time.
- **Added: 16 new tests** covering all v1.3.0 features (79 tests total).

### v1.2.0 (Bug Fixes)
- **CRITICAL FIX: Ctrl+J now works to clear paper jams** — Ctrl+J (ASCII 10 / Line Feed) was previously unreachable because the Enter handler caught `key == 10` first. Ctrl+J now takes priority: when jammed it clears the jam, when not jammed it acts as Line Feed (same as Enter).
- **FIX: Auto-type now auto-pauses on paper jam** — previously `_auto_type()` would silently skip characters when a jam occurred, losing text. Now it automatically pauses and waits for the user to clear the jam with Ctrl+J.
- **FIX: Ctrl+T (timestamp) disabled while jammed** — now a no-op while jammed.
- **FIX: Ctrl+E (export) now shows visual feedback** — "Exported!" or "Export failed!" on screen.
- **FIX: Escape sequence handling improved** — properly drains CSI sequences by reading until a final byte (0x40–0x7E).
- **Added: `_show_flash()` method** for displaying brief on-screen messages.
- **Added: 12 new tests** covering the fixed bugs.

### v1.1.0 (Enhanced)
- New: Paper jams, timestamp stamping, export to file, speed control, `--version` flag, `--demo` as proper argparse flag, word count in status bar.
- Improved: Error handling, comprehensive pytest suite, code comments, speed affects all delays.