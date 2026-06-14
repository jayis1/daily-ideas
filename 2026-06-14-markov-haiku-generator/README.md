# 🎋 Markov Chain Haiku Generator

A CLI tool that builds Markov chains from text input and generates **5-7-5 syllable haikus** (or **5-7-5-7-7 tanka poems**) with automatic season detection, syllable stats, colored terminal output, and file export.

## Description

This generator combines two fascinating techniques — **Markov chain text generation** and **English syllable counting** — to produce structurally correct poems from any text corpus. It ships with a built-in nature poetry corpus for immediate use, but can also train on your own text files to produce poems in any style or vocabulary.

The tool automatically detects the **season** (spring, summer, autumn, winter) of each generated poem based on keyword analysis, and decorates the output with matching emoji and color formatting.

## Features

- **Markov chain text generation** (configurable order 1–3)
- **Accurate English syllable counting** with 130+ word exception table for common poetic terms
- **5-7-5 haiku** and **5-7-5-7-7 tanka** generation — traditional Japanese poetic forms
- **Automatic season detection** with seasonal emoji (🌸🌿🍂❄️) and ANSI colors
- **Season filter** — `--season winter` biases output toward a specific season
- **Syllable stats** — `--stats` shows per-word syllable breakdown for every poem
- **Three display styles**: pretty (dynamic-width bordered box with emoji), CJK (Japanese-inspired dynamic-width frame), and minimal (plain lines)
- **Dynamic box widths** — CJK and pretty formats automatically adjust box width to fit line content, with truncation and ellipsis for very long lines
- **Interactive mode** — generate poems on demand, switch between haiku/tanka, cycle styles, add training text, view vocabulary stats
- **Built-in nature corpus** with 80+ poetic lines for out-of-the-box generation
- **Custom text training** — feed it any text file to change the vocabulary
- **File export** — `--export output.txt` saves all generated poems to a file
- **Reproducible output** with `--seed` flag
- **`--version` and `--help` flags**
- **Word repetition reduction** — recently-used words are deprioritized in generation
- **Robust input handling** — `train(None)` and `train(non-string)` are handled gracefully without crashing
- **No external dependencies** — pure Python 3.6+

## How to Install

No installation needed beyond Python 3.6+. Just clone and run:

```bash
git clone <repo-url>
cd markov-haiku-generator
```

Or simply copy `markov_haiku.py` to any directory.

## How to Run

### Generate a haiku from the built-in corpus

```bash
python3 markov_haiku.py
```

### Generate multiple haikus

```bash
python3 markov_haiku.py -n 5
```

### Generate a tanka (5-7-5-7-7)

```bash
python3 markov_haiku.py --tanka
```

### Train on a custom text file

```bash
python3 markov_haiku.py my_poems.txt -n 3
```

### Choose a display style

```bash
python3 markov_haiku.py -s cjk       # Japanese-inspired dynamic-width frame
python3 markov_haiku.py -s minimal   # Just the lines
python3 markov_haiku.py -s pretty    # Dynamic-width bordered box with emoji (default)
```

### Show syllable breakdown per word

```bash
python3 markov_haiku.py --stats -s minimal
```

Output:
```
Cherry blossoms fall
A frog jumps into the still
A cricket chirps in

  Line 1 (5): Cherry(2) blossoms(2) fall(1) ✓
  Line 2 (7): A(1) frog(1) jumps(1) into(2) the(1) still(1) ✓
  Line 3 (5): A(1) cricket(2) chirps(1) in(1) ✓
```

### Filter by season

```bash
python3 markov_haiku.py --season winter -n 3
python3 markov_haiku.py --season spring --tanka
```

### Export poems to a file

```bash
python3 markov_haiku.py -n 5 --export poems.txt
```

### Interactive mode

```bash
python3 markov_haiku.py -i
```

In interactive mode:
- **Enter** — Generate a new poem
- **t** — Switch to tanka mode (5-7-5-7-7)
- **h** — Switch back to haiku mode (5-7-5)
- **s** — Cycle display style (pretty → cjk → minimal)
- **c** — Enter custom training text (ended by an empty line)
- **d** — Reset to default corpus
- **v** — Show vocabulary stats
- **q** — Quit

### Reproducible output

```bash
python3 markov_haiku.py --seed 42 -n 3
```

### All options

```
usage: markov_haiku.py [-h] [-n COUNT] [-s {pretty,cjk,minimal}] [-i]
                       [-o ORDER] [--seed SEED]
                       [--season {spring,summer,autumn,winter}] [--tanka]
                       [--stats] [--export FILE] [--version]
                       [input_file]

positional arguments:
  input_file            Text file to train on

options:
  -h, --help            Show help message
  -n, --count COUNT     Number of poems to generate (default: 1)
  -s, --style           Output style: pretty, cjk, minimal (default: pretty)
  -i, --interactive     Interactive mode
  -o, --order ORDER     Markov chain order (default: 2)
  --seed SEED           Random seed for reproducibility
  --season              Filter poems to match a season
  --tanka               Generate tanka (5-7-5-7-7) instead of haiku (5-7-5)
  --stats               Show per-word syllable breakdown
  --export FILE         Save generated poems to a file
  --version             Show version number
```

## Usage Examples

**Pretty style haiku:**
```
  ☀️  ┌────────────────────────────────────┐
     │          A frog jumps into           │
     │    The temple bell echoes through    │
     │       Sunset paints the clouds       │
  ☀️  └────────────────────────────────────┘
      ── Summer ──
```

**CJK style tanka:**
```
  ╔══════════════════════════════════╗
  ║  A frog jumps into               ║
  ║  The temple bell echoes through  ║
  ║  Sunset paints the clouds        ║
  ║  Stars shine above the endless   ║
  ║  Snow melts quietly beneath the  ║
  ╚══════════════════════════════════╝
     🦋 Summer (tanka)
```

**Minimal style:**
```
Pine needles carpet
The fishing boat returns to
Sunset paints the sky
```

**Train on custom text:**
```bash
# Feed it sci-fi text for cyberpunk haikus
python3 markov_haiku.py cyberpunk_novel.txt -s cjk -n 5

# Train interactively
python3 markov_haiku.py -i
```

## How It Works

1. **Training**: The Markov chain reads input text and records word transition probabilities. Order-2 chains track pairs of preceding words for more natural output. A single-word fallback chain ensures generation always works even with limited vocabulary.

2. **Syllable counting**: A heuristic engine counts vowel groups, applies rules for silent-e, -ed endings, and consults an exception table for 130+ common poetic/nature words.

3. **Generation**: For each line, the generator attempts to produce a phrase matching the target syllable count (5, 7, or 5 for haiku; plus 7, 7 for tanka). It tries random Markov walks, evaluating all prefixes for a syllable match. If that fails, it falls back to constructing word-by-word using transition probabilities. Word repetition is reduced by deprioritizing recently-used words.

4. **Season detection**: Each poem's text is scanned for seasonal keywords (e.g., "cherry" → spring, "snow" → winter) and tagged with the matching season and emoji.

5. **Formatting**: The pretty and CJK styles dynamically calculate box width based on the longest line, ensuring proper alignment. Lines that exceed the maximum width are truncated with an ellipsis (…).

## File Structure

```
markov_haiku.py       — Main module (CLI + all logic)
test_markov_haiku.py  — Test suite (46 tests)
README.md             — This file
```

## Running Tests

```bash
python3 test_markov_haiku.py
```

All 46 tests cover: syllable counting, syllable breakdown, Markov chain training/generation, haiku structure enforcement, tanka generation, season detection, season bias filtering, formatting (pretty/CJK/minimal), CJK box alignment, stats display, custom training, reproducibility, empty input handling, order validation, None/non-string input handling, format_stats with mismatched line counts, Colors class, and version string.

## Changelog

### v1.1.1
- **Fixed CJK format box overflow** — Long poem lines (22+ characters) no longer break the ║ box alignment. The CJK format now dynamically calculates box width based on line content, with a max width of 40 characters and ellipsis truncation for very long lines.
- **Fixed pretty format potential overflow** — The pretty format now dynamically expands its border width to accommodate long lines, preventing misalignment.
- **Fixed `train(None)` crash** — `HaikuGenerator.train(None)` and `MarkovChain.train(None)` no longer crash. Both methods now explicitly check for `None` and non-string types before processing.
- **Fixed `format_stats` silent line dropping** — When `format_stats()` receives more lines than the target syllable pattern expects (e.g., 5 lines with `poem_type="haiku"`), it now shows the extra lines with their syllable counts instead of silently dropping them.
- **Added dynamic box width calculation** for both CJK and pretty formats.
- **Added ellipsis truncation** for lines exceeding maximum CJK box width.
- **Added 8 new tests** for the bug fixes (46 total, up from 38).

### v1.1.0
- Added **tanka mode** (`--tanka`) generating 5-7-5-7-7 poems
- Added **season filter** (`--season spring/summer/autumn/winter`)
- Added **syllable stats** (`--stats`) showing per-word breakdown
- Added **file export** (`--export`)
- Added **`--version` flag**
- Added **ANSI color output** with `NO_COLOR`/`FORCE_COLOR` support
- Added **word repetition reduction** in Markov chain generation
- Added **interactive mode** tanka switching and vocabulary stats
- Expanded **syllable exception table** (130+ words)
- Improved **error handling** for empty/missing files, invalid order
- Improved **docstrings** throughout the codebase
- Fixed **interactive custom training** to properly reset chain
- Increased **test suite** from 21 to 38 tests