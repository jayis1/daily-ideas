# ⌨ Terminal Typewriter Simulator

A fully interactive vintage typewriter simulator that runs right in your terminal. Experience the feel of typing on classic machines — from the satisfying clack of an Underwood No. 5 to the precision of an Olivetti Lettera 32 — complete with ink density variation, ribbon wear, and the iconic margin bell.

## Features

- **5 Authentic Typewriter Models** — each with unique keystroke speed, ink behavior, and margin bell positions:
  - Underwood No. 5 — the classic workhorse with heavy, satisfying keystrokes
  - Remington Portable — light and quick
  - Olivetti Lettera 32 — Italian design, smooth and precise
  - IBM Selectric II — the electric revolution, fast and consistent
  - Royal Quiet De Luxe — elegant but temperamental, with moody ink
- **Ink Density Simulation** — characters vary in darkness based on ribbon wear and random variation, just like a real typewriter
- **Ribbon Wear** — the longer you type, the fainter the ink gets. Install a fresh ribbon with `Ctrl+N`
- **Margin Bell** — hear the classic "ding" when approaching the right margin, just like a real typewriter
- **Overstrike Corrections** — press Backspace to overprint corrections (marked with ⌫)
- **CAPS LOCK Toggle** — `Ctrl+C` toggles caps lock
- **Auto-Type Mode** — feed text from the command line or a file and watch it type itself
- **Ink Colors** — choose black, red, blue, or green ink
- **Beautiful Paper Rendering** — your text appears on a white "page" with margins and a roller bar

## Installation

No external dependencies required — uses only Python's standard library (`curses`, `random`, `time`).

```bash
# Clone or download the project
cd daily-ideas/2026-07-17-terminal-typewriter/

# Make executable (optional)
chmod +x typewriter.py
```

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
python3 typewriter.py -f letter.txt
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
| **Q** | Quit |

## Usage Examples

### Compose a letter on the Royal Quiet De Luxe

```bash
python3 typewriter.py -m royal
```

### Auto-type a file with blue ink on the Olivetti

```bash
python3 typewriter.py -m olivetti -c blue -f my_poem.txt
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

1. **Keystroke Timing** — Each model has different min/max delay ranges. The Underwood No. 5 has heavy, slow keys (0.03–0.09s), while the IBM Selectric II is fast and electric (0.015–0.05s). Random variation simulates human typing, with occasional longer pauses for finger repositioning.

2. **Ink Density** — Every character's ink density is calculated from the ribbon's wear level plus a Gaussian random variable. Fresh ribbons produce bold, dark text; worn ribbons produce faint, uneven impressions. The ink variance parameter differs per model — the Royal has high variance (moody ink), the IBM has low variance (consistent).

3. **Ribbon Wear** — The ribbon degrades slowly with each character typed (0.02% per character). After ~5000 characters, text starts getting noticeably fainter. Press `Ctrl+N` to install a fresh ribbon.

4. **Margin Bell** — Each model has a different "ding at" column (where the bell rings to warn you about the right margin). The Underwood dings at column 65, the IBM at 75. This matches the physical margin settings of each machine.

5. **Overstrike Corrections** — Rather than erasing, backspace overstrikes with a ⌫ character, mimicking how real typists corrected mistakes by typing X over the error.

## Requirements

- Python 3.6+
- A terminal with curses support (most Linux/macOS terminals)
- For the best experience: a terminal that supports colors and terminal bell

## Files

- `typewriter.py` — Main application (interactive + demo modes)
- `test_typewriter.py` — Unit tests for core functionality
- `test_demo.py` — Demo script showing all 5 typewriter models
- `sample_letter.txt` — Sample text file for auto-type testing