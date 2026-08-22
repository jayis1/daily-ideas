# Keyboard Heatmap Analyzer

Keyboard Heatmap Analyzer is a small terminal utility that turns any text into a visual map of which keys you use most on a QWERTY keyboard. It is part typing microscope, part ergonomic curiosity, and part fun text visualizer.

## What it does

Given direct text, a text file, or a built-in preset, the program:

- counts how often each keyboard key is used
- renders an ANSI-colored keyboard heatmap in the terminal
- summarizes row usage, hand balance, and finger hotspots
- reports the most common keys and bigrams
- highlights same-finger bigrams, which are often awkward to type

It works with standard letters, digits, punctuation, and spaces using a normalized US QWERTY layout.

## Features

- Pure Python, no dependencies
- Colorful terminal heatmap
- File input support
- Built-in presets for quick demos
- Useful typing statistics
- Easy to extend for other layouts

## Installation

Python 3.11+ is recommended.

```bash
cd ~/daily-ideas/2026-08-22-keyboard-heatmap-analyzer
python3 -m pip install pytest  # optional, only for running tests
```

The app itself needs only the Python standard library.

## How to run

### Analyze a custom sentence

```bash
python3 keyboard_heatmap.py "the quick brown fox jumps over the lazy dog"
```

### Analyze a file

```bash
python3 keyboard_heatmap.py --file README.md
```

### Run a built-in demo preset

```bash
python3 keyboard_heatmap.py --preset code
```

### Disable ANSI colors

```bash
python3 keyboard_heatmap.py --preset poem --no-color
```

## Usage

```text
usage: keyboard_heatmap.py [-h] [--file FILE] [--preset {code,pangram,poem}] [--top TOP] [--no-color] [text ...]
```

### Options

- `text`: free-form text to analyze
- `--file`: load UTF-8 text from a file
- `--preset`: analyze one of the included demo texts
- `--top`: number of top keys/bigrams/fingers to list
- `--no-color`: print a plain-text heatmap without ANSI colors

## Example output

```bash
python3 keyboard_heatmap.py --preset pangram --no-color
```

This prints:

- a keyboard-shaped table where hot keys have larger counts
- totals for mapped characters and unique keys
- row usage percentages
- left/right hand balance
- the busiest fingers
- the most common keys and bigrams

## Project structure

- `keyboard_heatmap.py` — main CLI program
- `test_keyboard_heatmap.py` — lightweight automated tests
- `README.md` — project documentation

## Why it is interesting

Most text tools show frequencies as plain lists. This project places those frequencies back onto the physical keyboard, which makes writing style and ergonomic patterns immediately visible. Code samples, poetry, and prose all produce noticeably different heat signatures.

## Running tests

```bash
pytest -q
```

## Ideas for extension

- add Dvorak or Colemak layouts
- compare two texts side by side
- export heatmaps as HTML
- score text for typing comfort
