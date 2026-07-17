# ⌨ Terminal Typewriter Simulator

**v1.1.0**

A fully interactive vintage typewriter simulator that runs right in your terminal. Experience the feel of typing on classic machines — from the satisfying clack of an Underwood No. 5 to the precision of an Olivetti Lettera 32 — complete with ink density variation, ribbon wear, paper jams, and the iconic margin bell.

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
- **Margin Bell** — hear the classic "ding" when approaching the right margin, just like a real typewriter
- **Overstrike Corrections** — press Backspace to overprint corrections (marked with ⌫)
- **Paper Jams** — random jam events that block typing until you clear them with `Ctrl+J` (jam frequency varies by model — the Royal jams most, the IBM Selectric almost never)
- **CAPS LOCK Toggle** — `Ctrl+C` toggles caps lock
- **Timestamp Stamping** — `Ctrl+T` inserts the current date and time
- **Speed Control** — adjust auto-type playback speed from 0.1x to 10x with `--speed`
- **Export to File** — save your typed work to a file with `--export`
- **Word & Character Count** — live word count in the status bar
- **Auto-Type Mode** — feed text from the command line or a file and watch it type itself
- **Ink Colors** — choose black, red, blue, or green ink
- **Beautiful Paper Rendering** — your text appears on a white "page" with margins and a roller bar

## Installation

No external dependencies required — uses only Python's standard library (`curses`, `random`, `time`, `argparse`).

```bash
cd daily-ideas/2026-07-17-terminal-typewriter/

# Make executable (optional)
chmod +x typewriter.py
```

**Requirements:** Python 3.6+ and a terminal with curses support (most Linux/macOS terminals). For the best experience, use a terminal that supports colors and the terminal bell.

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

### Export Typed Content to File

```bash
# Everything you type will be saved to output.txt when you quit
python3 typewriter.py --export my_letter.txt

# Combine with auto-type for conversion
python3 typewriter.py -f input.txt --export output.txt -s 5.0
```

### Demo Mode (non-interactive)

```bash
python3 typewriter.py --demo
```

Prints a static typewriter-styled demo to stdout (no curses required).

### Disable Bell

```bash
python3 typewriter.py --quiet
```

### Show Version

```bash
python3 typewriter.py --version
# Output: Terminal Typewriter Simulator v1.1.0
```

### Show Help

```bash
python3 typewriter.py --help
```

## Interactive Controls

| Key | Action |
|-----|--------|
| **Any printable key** | Type that character |
| **Enter** | Carriage return + line feed |
| **Backspace** | Overstrike last character (correction) |
| **Ctrl+U** | New line |
| **Ctrl+R** | Carriage return (no line feed) |
| **Ctrl+D** | Ring the bell manually |
| **Ctrl+N** | Install a fresh ribbon (reset ink density) |
| **Ctrl+P** | Pause/resume auto-type |
| **Ctrl+C** | Toggle CAPS LOCK |
| **Ctrl+T** | Insert timestamp (date + time) |
| **Ctrl+J** | Clear paper jam |
| **Ctrl+E** | Export to file (if `--export` set) |
| **Q** | Quit (auto-exports if `--export` is set) |

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

### Quick demo to see what it looks like

```bash
python3 typewriter.py --demo
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

  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
```

## How It Works

The simulator models several aspects of a real typewriter:

1. **Keystroke Timing** — Each model has different min/max delay ranges. The Underwood No. 5 has heavy, slow keys (0.03–0.09s), while the IBM Selectric II is fast and electric (0.015–0.05s). Random variation simulates human typing, with occasional longer pauses for finger repositioning. The `--speed` flag multiplies playback speed.

2. **Ink Density** — Every character's ink density is calculated from the ribbon's wear level plus a Gaussian random variable. Fresh ribbons produce bold, dark text; worn ribbons produce faint, uneven impressions. The ink variance parameter differs per model — the Royal has high variance (moody ink), the IBM has low variance (consistent).

3. **Ribbon Wear** — The ribbon degrades slowly with each character typed (0.02% per character). After ~5000 characters, text starts getting noticeably fainter. Press `Ctrl+N` to install a fresh ribbon.

4. **Margin Bell** — Each model has a different "ding at" column (where the bell rings to warn you about the right margin). The Underwood dings at column 65, the IBM at 75. This matches the physical margin settings of each machine.

5. **Paper Jams** — Each model has a per-character chance of jamming. The Royal (temperamental!) has the highest jam rate at 0.4%, while the IBM Selectric (electric and reliable) has the lowest at 0.03%. When jammed, no characters can be typed until you clear it with `Ctrl+J`, which produces a satisfying bell acknowledgment.

6. **Overstrike Corrections** — Rather than erasing, backspace overstrikes with a ⌫ character, mimicking how real typists corrected mistakes by typing X over the error.

7. **Timestamps** — Press `Ctrl+T` to insert a `--- YYYY-MM-DD HH:MM ---` timestamp line, just like stamping a date on a letter.

8. **Export** — When `--export FILE` is set, your typed content is automatically saved to that file when you quit. You can also press `Ctrl+E` to save mid-session.

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

## Files

| File | Description |
|------|-------------|
| `typewriter.py` | Main application (interactive + demo modes) |
| `test_typewriter.py` | Comprehensive unit tests (51 tests) |
| `test_demo.py` | Demo script showing all 5 typewriter models |
| `sample_letter.txt` | Sample text file for auto-type testing |

## Changelog

### v1.1.0 (Enhanced)
- **New: Paper jams** — random jam events with model-specific frequencies; clear with `Ctrl+J`
- **New: Timestamp stamping** — insert date/time with `Ctrl+T`
- **New: Export to file** — `--export FILE` saves typed content; `Ctrl+E` mid-session save
- **New: Speed control** — `--speed FLOAT` adjusts auto-type rate from 0.1x to 10x
- **New: `--version` flag** — shows version number
- **New: `--demo` as proper argparse flag** — no longer a raw `sys.argv` check
- **New: Word count** in status bar
- **Improved: Error handling** — `PermissionError` handling for file reads, graceful fallback for terminal bell
- **Improved: Tests** — comprehensive pytest suite with 51 parametrized tests
- **Improved: Code comments** — thorough docstrings and inline explanations
- **Improved: Speed affects all delays** — carriage return, margin bell pause, auto-type all respect speed multiplier