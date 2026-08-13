# Terminal Semaphore Flag Signaler

A CLI tool that translates text into maritime flag semaphore positions and visualizes them as animated ASCII stick figures holding flags. Each letter of the alphabet is represented by holding two flags in specific compass directions — this tool brings that centuries-old signaling system to life in your terminal.

**Version 2.1.0** — includes decoding, ANSI color, JSON output, file export, special signals, and a comprehensive test suite.

## What is Flag Semaphore?

Flag semaphore is a system of conveying information at a distance by means of visual signals with hand-held flags. It's still used today by the Navy and in scouting. The signaler holds two flags, each in one of 8 compass positions (like the spokes of a wheel), and the combination of the two positions encodes a letter, digit, or command.

```
       6    7    8
        \  |  /
     5-- O --1
        /  |  \
       4    3    2
```

Each letter is a unique pair of two positions (one per arm). For example:
- **A** = flags at positions 1 (down) and 8 (down-left)
- **B** = flags at positions 1 (down) and 7 (left)
- **S** = flags at positions 4 (up-right) and 8 (down-left)

## Features

### Core
- **Animated ASCII rendering** — a stick figure with head, torso, legs, and two arms holds flags at the correct angles for each character
- **Full alphabet support** — all 26 letters (A–Z) encoded per the ITU semaphore standard
- **Number mode** — digits 0–9 are encoded using the "numerals" preamble (J position) followed by letter-based codes
- **Compass diagram** — each frame shows a small diagram highlighting the active positions with names

### Encoding & Decoding
- **Text → Semaphore** (`--encode`, `--json`, animation) — encode text into flag position pairs
- **Semaphore → Text** (`--decode`) — decode position pairs back into text with smart J-position disambiguation (J as a letter vs. J as the numerals preamble)
- **Multiple input formats** for decoding: space, semicolon, colon separators between pairs; comma, dash, slash within pairs; or compact two-digit tokens

### Visualization
- **ANSI color output** — colorful stick figure with cyan head, white torso/legs, yellow left arm, green right arm (`--color`)
- **Compass diagram** — highlights active positions with `[brackets]` and shows position names
- **Loop mode** — repeat the animation continuously

### Output Modes
- **Animated mode** — frame-by-frame animation of your text (default)
- **Encode mode** — text-only output of positions (`--encode`)
- **JSON mode** — structured JSON output of all frames (`--json`)
- **Export mode** — save all frames (with figures and diagrams) to a text file (`--export`)
- **Chart mode** — print the complete semaphore alphabet reference (`--chart`)
- **Special signals mode** — print the reference table for special semaphore commands (`--special`)
- **Interactive mode** — REPL for encoding multiple messages
- **File mode** — signal the contents of a file (`--file`)

### CLI
- **`--help`** with usage examples
- **`--version`** flag
- **`--delay`** to control animation speed (validated: must be positive for animation)
- **`--no-diagram`** to hide the compass diagram
- **`--color`** to enable ANSI color output

## Installation

No external dependencies required — pure Python standard library only.

```bash
cd ~/daily-ideas/2026-08-13-terminal-semaphore-signaler
python3 semaphore.py --help
```

Requires Python 3.6+ (uses `math`, `argparse`, `os`, `sys`, `time`, `string`, `json`, `re` — all standard library).

## How to Run

### Basic usage — animate text

```bash
python3 semaphore.py "SOS HELLO"
```

This clears the screen and shows an animated stick figure signaling each character, one frame at a time.

### With color

```bash
python3 semaphore.py "SOS HELLO" --color
```

### Encode mode (text only, no animation)

```bash
python3 semaphore.py "SOS" --encode
```

Output:
```
Text: SOS
Frames: 3
----------------------------------------
     'S'  ->  L=4  R=8   (Letter 'S')
     'O'  ->  L=3  R=7   (Letter 'O')
     'S'  ->  L=4  R=8   (Letter 'S')
```

### JSON output

```bash
python3 semaphore.py "SOS" --json
```

Output:
```json
{
  "text": "SOS",
  "frame_count": 3,
  "frames": [
    {"char": "S", "left_position": 4, "right_position": 8, "label": "Letter 'S'"},
    {"char": "O", "left_position": 3, "right_position": 7, "label": "Letter 'O'"},
    {"char": "S", "left_position": 4, "right_position": 8, "label": "Letter 'S'"}
  ]
}
```

### Decode mode (positions → text)

```bash
python3 semaphore.py --decode "4,8 3,7 4,8"
```

Output:
```
  Decoded: SOS
```

Accepts multiple separator formats:
- **Between pairs**: spaces, semicolons, colons — e.g. `"4,8 3,7"`, `"4,8;3,7"`, `"4,8:3,7"`
- **Within pairs**: commas, dashes, slashes — e.g. `"4,8"`, `"4-8"`, `"4/8"`
- **Compact**: two-digit tokens without separator — e.g. `"48 37 48"`

The decoder intelligently handles the ambiguous J position (2,6): if the next frame decodes as a digit-mapped letter (A–I), J is treated as the numerals preamble; otherwise it's decoded as the letter J.

### Export frames to a file

```bash
python3 semaphore.py "HELLO WORLD" --export output.txt
```

ANSI color codes are stripped from the exported file for clean text output.

### Print the full semaphore chart

```bash
python3 semaphore.py --chart
```

### Print special signals reference

```bash
python3 semaphore.py --special
```

Output:
```
  Special Semaphore Signals
  ==================================================

  Signal       | Positions | Description
  -------------|-----------|---------------------------
  REST         |   1, 1    | Both arms down — rest / attention
  ATTENTION    |   5, 5    | Both flags up — start of message / attention
  ERROR        |   4, 8    | Flags crossed — error / cancel last character
  CORRECT      |   2, 4    | Acknowledge / correct / ready to receive
  NUMERALS     |   2, 6    | Switch to number mode (same as J position)
  LETTERS      |   3, 6    | Return to letter mode (same as P position)
```

### Interactive mode

```bash
python3 semaphore.py
```

Then type text and press Enter to signal it. Special commands:
- `:demo` — run a demo sequence ("SOS HELLO 42")
- `:chart` — show the full semaphore chart
- `:file path.txt` — signal the contents of a file
- `:decode 1,8 1,7` — decode position pairs to text
- `:special` — show special semaphore signals
- `:color` — toggle ANSI color output
- `:help` — show available commands
- `:quit` — exit

### File mode

```bash
python3 semaphore.py --file message.txt
```

### Loop the animation

```bash
python3 semaphore.py "HELLO WORLD" --loop
```

### Adjust animation speed

```bash
python3 semaphore.py "HELLO" --delay 0.5   # faster
python3 semaphore.py "HELLO" --delay 2.0   # slower
```

Note: `--delay` must be a positive number for animation mode. A non-positive value will produce an error.

## Usage Examples

```bash
# Signal a distress call
python3 semaphore.py "SOS"

# Signal with color
python3 semaphore.py "HELLO WORLD" --color

# Signal a message with numbers
python3 semaphore.py "AGENT 007"

# Signal a longer message slowly
python3 semaphore.py "THE EAGLE HAS LANDED" --delay 2.0

# Get the encoding without animation
python3 semaphore.py "HELLO WORLD" --encode

# Get machine-readable JSON output
python3 semaphore.py "HELLO WORLD" --json | jq '.frames[]'

# Decode positions back to text (various formats)
python3 semaphore.py --decode "1,8 1,7 3,7"
python3 semaphore.py --decode "1,8;1,7;3,7"
python3 semaphore.py --decode "1,8:1,7:3,7"
python3 semaphore.py --decode "18 17 37"
python3 semaphore.py --decode "4-8 3-7 4-8"

# Decode letter J (not numerals preamble)
python3 semaphore.py --decode "2,6"
# Output: Decoded: J

# Decode digit sequence (J as numerals preamble)
python3 semaphore.py --decode "2,6 1,8"
# Output: Decoded: 1

# Export frames to a file
python3 semaphore.py "SOS" --export signal.txt

# Print the reference chart
python3 semaphore.py --chart

# Print special signals
python3 semaphore.py --special

# Interactive session
python3 semaphore.py
> SOS
> :demo
> :color
> HELLO
> :decode 4,8 3,7 4,8
> :quit
```

## How It Works

1. **Encoding**: The `encode_text()` function takes input text and converts each character to a `(left_position, right_position)` pair. Letters map directly via the semaphore table. Digits trigger a "numerals" preamble (the J position) followed by the corresponding letter code. Spaces produce the "rest" position (both arms down).

2. **Decoding**: The `decode_positions()` function reverses the process. It builds a reverse lookup table from the semaphore alphabet (supporting both left/right orderings), and uses **lookahead** to disambiguate the J position: if the next frame decodes as a digit-mapped letter (A–I), J is treated as the numerals preamble; otherwise it's decoded as the letter J. The `decode_position_string()` helper parses various separator formats.

3. **Rendering**: For each frame, a 40×22 character canvas is created. A stick figure is drawn with a circular head (`@`), vertical torso (`|`), diagonal legs (`\` and `/`), and two arms drawn as lines (`-`) using Bresenham's line algorithm. Flag tips are marked with `#` characters. The arm angle is computed from the semaphore position number using trigonometry. In color mode, ANSI escape codes are applied: cyan head, white torso/legs, yellow left arm/flag, green right arm/flag.

4. **Animation**: The `animate()` function clears the screen, renders each frame, displays it with the compass diagram and character info, then waits for the configured delay before advancing to the next frame.

5. **Export**: The `export_frames()` function writes all frames (with figures and diagrams) to a text file, stripping ANSI codes for clean output using a regex-based `strip_ansi()` helper.

## Semaphore Position Reference

```
Position 1 = straight down         (angle: -90°)
Position 2 = down-right            (angle: -45°)
Position 3 = right / horizontal    (angle:   0°)
Position 4 = up-right              (angle:  45°)
Position 5 = straight up           (angle:  90°)
Position 6 = up-left               (angle: 135°)
Position 7 = left / horizontal     (angle: 180°)
Position 8 = down-left             (angle: 225°)
```

## Special Signals

| Signal | Positions | Description |
|--------|-----------|-------------|
| REST | 1, 1 | Both arms down — rest / attention |
| ATTENTION | 5, 5 | Both flags up — start of message / attention |
| ERROR | 4, 8 | Flags crossed — error / cancel last character |
| CORRECT | 2, 4 | Acknowledge / correct / ready to receive |
| NUMERALS | 2, 6 | Switch to number mode (same as J position) |
| LETTERS | 3, 6 | Return to letter mode (same as P position) |

## Testing

```bash
cd ~/daily-ideas/2026-08-13-terminal-semaphore-signaler
python3 test_semaphore.py
```

The test suite (**68 tests**) covers:
- All 26 letters have valid, non-conflicting semaphore mappings
- 8 flag positions with unique angles and names
- Letter encoding (uppercase, lowercase, empty string, punctuation)
- Space → rest position
- Digit encoding with numeral preamble (single and multi-digit)
- Unknown character handling
- **Decoding** — basic letters, reversed order, spaces, digits, unknown pairs, round-trip
- **J-position disambiguation** — J as letter, J as numerals preamble, J in number mode (decodes as 0)
- **Position string parsing** — spaces, semicolons, dashes, colons, compact digits
- **Special signals** — all 6 signals defined with valid positions
- Figure rendering dimensions and content (colored and uncolored)
- Different positions produce different renders
- Colored figure contains ANSI escape codes
- **Diagram rendering** — all 8 positions correctly bracketed
- Angle-to-delta conversion for all cardinal directions
- Canvas and line-drawing primitives
- Line pixels helper function
- Color utility functions (enabled, disabled, unknown colors)
- `strip_ansi` and `visible_len` helpers
- **CLI parser**: `--version`, `--color`, `--json`, `--decode`, `--export`, `--special` flags
- **Colored display frame border width** — verifies border is not inflated by ANSI codes
- **Negative delay rejection** — verifies `--delay -1` is rejected for animation
- File export with and without diagrams
- Version string validation

## Files

| File | Description |
|------|-------------|
| `semaphore.py` | Main program — encoder, decoder, renderer, animator, CLI |
| `test_semaphore.py` | 68-test suite covering all functionality |
| `README.md` | This file |

## Changelog

### v2.1.0 — Bug Fixes
- **Fixed: Letter J could not be decoded** — The J position (2,6) was always treated as the numerals preamble, making it impossible to decode the letter J. Added lookahead logic: J is only treated as numerals preamble if the next frame decodes as a digit-mapped letter (A–I); otherwise it decodes as the letter J.
- **Fixed: Diagram bracket positions wrong for positions 2, 3, 7, 8** — The `pos_coords` dictionary in `render_diagram()` had incorrect grid coordinates for positions 2 (was 19, should be 16), 3 (was 12, should be 11), 7 (was 12, should be 11), and 8 (was 18, should be 16). Brackets appeared at wrong locations or not at all.
- **Fixed: Interactive `:decode` off-by-one** — `text[9:]` was used instead of `text[8:]`, causing the first character of the decode argument to be stripped. `":decode "` is 8 characters, so `text[8:]` correctly starts at the argument.
- **Fixed: Colored display border width inflated** — `display_frame()` calculated border width using raw string length including ANSI escape codes, producing borders ~89 chars wide instead of ~44. Added `strip_ansi()` and `visible_len()` helpers and used them for width calculations.
- **Fixed: `decode_position_string` failed with mixed separators** — `"1,8:1,7"` was parsed incorrectly because colon was treated as a within-pair separator alongside comma. Reworked to properly distinguish between-pair separators (whitespace, semicolons, colons) from within-pair separators (commas, dashes, slashes).
- **Fixed: Compact digit tokens not parsed** — `"18 17"` (two-digit tokens without separator) produced empty output. Added fallback parsing for two-digit tokens.
- **Fixed: Negative delay crashed animation** — `time.sleep()` raises `ValueError` for negative values. Added validation in `main()` (rejects with error message) and a safety guard in `animate()`.
- **Improved**: Export ANSI stripping now uses regex-based `strip_ansi()` instead of manual string replacement.
- **Added**: 11 regression tests covering all bug fixes (57 → 68 tests total).

### v2.0.0 — Feature Enhancements
- Added decoding mode (`--decode`)
- Added ANSI color output (`--color`)
- Added JSON output (`--json`)
- Added file export (`--export`)
- Added special signals (`--special`)
- Added `--version` flag
- Added position names in diagram
- Added interactive mode commands: `:decode`, `:special`, `:color`, `:help`
- Improved CLI with examples in `--help`
- Added comprehensive test suite (57 tests)

### v1.0.0 — Initial Release
- Basic semaphore encoding and animation
- Interactive mode
- Chart display
- File input mode

## Educational Notes

Semaphore flag signaling dates back to the early 19th century and was widely used by naval forces before the advent of radio. It remains a practical skill in scouting and naval training. This tool serves as both a learning aid for the semaphore alphabet and a demonstration of how visual encoding systems work.

The ITU (International Telecommunication Union) standardized the flag semaphore system, and the encoding used here follows that standard. The special signals (Attention, Error, Correct, etc.) are based on standard semaphore operational commands used in practice.

## License

Free to use, modify, and distribute. Part of the daily-ideas project collection.