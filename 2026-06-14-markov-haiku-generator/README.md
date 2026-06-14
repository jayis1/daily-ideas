# 🎋 Markov Chain Haiku Generator

A CLI tool that builds Markov chains from text input and generates **5-7-5 syllable haikus** with automatic season detection and beautiful terminal formatting.

## Description

This generator combines two fascinating techniques — **Markov chain text generation** and **English syllable counting** — to produce structurally correct haikus from any text corpus. It ships with a built-in nature poetry corpus for immediate use, but can also train on your own text files to produce haikus in any style or vocabulary.

The tool automatically detects the **season** (spring, summer, autumn, winter) of each generated haiku based on keyword analysis, and decorates the output with matching emoji and formatting.

## Features

- **Markov chain text generation** (configurable order 1–3)
- **Accurate English syllable counting** with exception table for common poetic words
- **5-7-5 syllable enforcement** — every haiku follows the traditional structure
- **Automatic season detection** with seasonal emoji (🌸🌿🍂❄️)
- **Three display styles**: pretty (boxed), CJK (Japanese-inspired), and minimal
- **Built-in nature corpus** with 80+ poetic lines for out-of-the-box generation
- **Custom text training** — feed it any text file to change the vocabulary
- **Interactive mode** — generate haikus on demand, cycle styles, add training text
- **Reproducible output** with `--seed` flag
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

### Train on a custom text file

```bash
python3 markov_haiku.py my_poems.txt -n 3
```

### Choose a display style

```bash
python3 markov_haiku.py -s cjk       # Japanese-inspired box
python3 markov_haiku.py -s minimal   # Just the lines
python3 markov_haiku.py -s pretty    # Bordered box with emoji (default)
```

### Interactive mode

```bash
python3 markov_haiku.py -i
```

In interactive mode, press Enter to generate haikus, `s` to cycle styles, `c` to add custom training text, `d` to reset to the default corpus, and `q` to quit.

### Reproducible output

```bash
python3 markov_haiku.py --seed 42 -n 3
```

## Usage Examples

**Pretty style:**
```
  🍂  ┌────────────────────────────────────────┐
     │         Crimson leaves fall             │
     │     A frog jumps into the still         │
     │         A cricket chirps in             │
  🍂  └────────────────────────────────────────┘
      ── Autumn ──
```

**CJK style:**
```
  ╔══════════════════════════╗
  ║  A caterpillar          ║
  ║  Gentle waves lap against║
  ║  The bamboo forest       ║
  ╚══════════════════════════╝
     🌿 Summer
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
```

## How It Works

1. **Training**: The Markov chain reads input text and records word transition probabilities. Order-2 chains track pairs of preceding words for more natural output.

2. **Syllable counting**: A heuristic engine counts vowel groups, applies rules for silent-e, -ed endings, and consults an exception table for ~100 common poetic/nature words.

3. **Generation**: For each line, the generator attempts to produce a phrase matching the target syllable count (5, 7, or 5). It tries random Markov walks, evaluating all prefixes for a syllable match. If that fails, it falls back to constructing word-by-word using transition probabilities.

4. **Season detection**: Each haiku's text is scanned for seasonal keywords (e.g., "cherry" → spring, "snow" → winter) and tagged with the matching season and emoji.

## File Structure

```
markov_haiku.py       — Main module (CLI + all logic)
test_markov_haiku.py  — Test suite (21 tests)
README.md             — This file
```

## Running Tests

```bash
python3 test_markov_haiku.py
```

All 21 tests cover syllable counting, Markov chain training/generation, haiku structure enforcement, formatting, season detection, custom training, and reproducibility.